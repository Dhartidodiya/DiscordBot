import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from imblearn.over_sampling import SMOTE

class MLViewModel:
    def __init__(self, data_model):
        self.data_model = data_model
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.model = LogisticRegression(class_weight='balanced')

    def train_model(self):
        """Train the machine learning model using data from the SQLite database."""
        conn = sqlite3.connect("messages.db")
        data = pd.read_sql_query("SELECT content AS Message, is_report AS Is_Report FROM messages", conn)

        if data.empty:
            print("⚠ No data available for training.")
            return 0.0

        data['Message'] = data['Message'].str.lower().fillna('')
        X = data['Message']
        y = data['Is_Report']

        X_tfidf = self.vectorizer.fit_transform(X).toarray()

        print("\nClass distribution before SMOTE:", y.value_counts())
        
        if len(y.unique()) <= 1:
            print("⚠ SMOTE cannot be applied. Only one class present in the target variable.")
            return 0.0

        smote = SMOTE(random_state=42)
        X_balanced, y_balanced = smote.fit_resample(X_tfidf, y)
        print("Class distribution after SMOTE:", pd.Series(y_balanced).value_counts())

        X_train, X_test, y_train, y_test = train_test_split(X_balanced, y_balanced, test_size=0.3, random_state=42)
        self.model.fit(X_train, y_train)
        y_pred = self.model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        print("\nModel Accuracy:", accuracy)
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))
        print("\nConfusion Matrix:")
        print(confusion_matrix(y_test, y_pred))
        return accuracy * 100
