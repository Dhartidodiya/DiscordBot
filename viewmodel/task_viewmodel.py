# /viewmodel/task_viewmodel.py
import re
from transformers import T5ForConditionalGeneration, T5Tokenizer,pipeline
from deep_translator import GoogleTranslator
from datetime import datetime, timedelta



class TaskViewModel:
    def __init__(self):
        model_name = "t5-large"
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        
        # Initialize XLM-R model for language detection
        self.language_identifier = pipeline("text-classification", model="papluca/xlm-roberta-base-language-detection")

    def preprocess_content(self, content):
        """Preprocess the content by removing mentions and unwanted characters."""
        content = re.sub(r'<@!?[0-9]+>', '', content)  # Remove user mentions
        content = re.sub(r'<@&[0-9]+>', '', content)   # Remove role mentions
        content = re.sub(r'[^a-zA-Z0-9/\-\s]', '', content)  # Keep alphanumeric, slashes, dashes, and spaces
        content = re.sub(r'\s+', ' ', content)  # Replace multiple spaces with a single space
        return content.strip()
  
  
  
    def detect_language(self, text):
        """Detect the language of a given text using XLM-R."""
        try:
            result = self.language_identifier(text)
            print(f"Raw result from XLM-R language detection model: {result}")  # Debug: Print the raw result
            
            detected_lang = result[0]['label'].lower()  # Convert label to lowercase (e.g., "EN" -> "en")
            print(f"Detected language code: {detected_lang}")  # Debug: Print the detected language code
            
            
            return detected_lang
        except Exception as e:
            print(f"Error detecting language with XLM-R: {e}")
            return 'unknown'
        
    def translate(self, text, source_language, target_language):
        """Translate text from source_language to target_language."""
        
        if source_language == target_language or source_language == 'unknown':
            return text  # Skip translation if languages are the same or source language is unknown
        
        try:
            translated_text = GoogleTranslator(source=source_language, target=target_language).translate(text)
            return translated_text
        except Exception as e:
            print(f"Error translating text: {e}")
            return text
        
    def translate_if_needed(self, text, source_language, target_language):
        """Translate the text if the source language differs from the target language."""
        
        if not text or not source_language or not target_language:
            return text
        
        if source_language != target_language and target_language != 'unknown':
            print(f"Translating from '{source_language}' to '{target_language}'")
            return self.translate(text, source_language, target_language)
        
        # Debug print to indicate no translation was needed
        print(f"No translation needed for text: {text[:50]}")
        return text
 
    def extract_date_from_message(self, message_content):
        """Extract date from the message if present, including handling 'till date'."""
        # Pattern for dates in format '11/08/2024' or '11082024'
        date_pattern = r'(\d{2}[/-]\d{2}[/-]\d{4})'
        match = re.search(date_pattern, message_content)

        if match:
            date_str = match.group(1)
            try:
                extracted_date = datetime.strptime(date_str, '%d/%m/%Y')
                return extracted_date.strftime('%Y-%m-%d')
            except ValueError:
                return None

        # Handle 'today', 'yesterday', and 'tomorrow' in English and French
        if any(keyword in message_content.lower() for keyword in ['today', "aujourd'hui"]):
            return datetime.now().strftime('%Y-%m-%d')

        if any(keyword in message_content.lower() for keyword in ['yesterday', 'hier']):
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        if any(keyword in message_content.lower() for keyword in ['tomorrow', 'demain']):
            return (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Handle "till" or "jusqu'à" patterns for till date detection
        till_pattern = r'(till|jusqu\'à) (\d{2}[/-]\d{2}[/-]\d{4})'
        match_till = re.search(till_pattern, message_content.lower())

        if match_till:
            date_str = match_till.group(2)
            try:
                extracted_date = datetime.strptime(date_str, '%d/%m/%Y')
                return extracted_date.strftime('%Y-%m-%d')
            except ValueError:
                return None

        # Pattern for dates without slashes (e.g., '11082024')
        no_slash_pattern = r'\b(\d{2})(\d{2})(\d{4})\b'
        match_no_slash = re.search(no_slash_pattern, message_content)

        if match_no_slash:
            day, month, year = match_no_slash.groups()
            try:
                extracted_date = datetime.strptime(f'{day}/{month}/{year}', '%d/%m/%Y')
                return extracted_date.strftime('%Y-%m-%d')
            except ValueError:
                return None

        return None



    def prioritize_tasks(self, task_text):
        """Identify and prioritize tasks based on keywords."""
        high_priority_keywords = ['urgent', 'important', 'high priority', 'asap']
        prioritized_tasks = [f"[PRIORITY] {task}" if any(keyword in task.lower() for keyword in high_priority_keywords) else task for task in task_text.split(",")]
        return ", ".join(prioritized_tasks)
    



    def summarize_with_t5(self, text, max_length=100):
        """Summarize text using the T5 model."""
        inputs = self.tokenizer.encode(f"summarize: {text}", return_tensors="pt", max_length=512, truncation=True)
        summary_ids = self.model.generate(inputs, max_length=max_length, min_length=30, length_penalty=2.0, num_beams=4, early_stopping=True)
        summarized_text = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        sentences = [sentence.strip() for sentence in summarized_text.split('.') if sentence.strip()]
        return "\n".join([f"{sentence.strip()}." for sentence in sentences])
    

    def format_task_summary(self, author, tasks_summary, include_date=False):
        """Format task summary for a user with channel names on new lines and bullet points for tasks."""
        
        
        header = f"\nUser: {author}\n"
        formatted_summary = []

        # Process each channel's tasks
        for channel, tasks in tasks_summary.items():
            formatted_summary.append(f"\n{channel}:")  # Start the channel with the name alone on a new line

            # Add each task with a bullet point
            for task in tasks:
                if isinstance(task, tuple):
                    task_content, task_date = task  # Unpack tuple values
                    if include_date:
                        # Ensure task_date is formatted as DD/MM/YYYY
                        try:
                            formatted_date = datetime.strptime(task_date, '%Y-%m-%d').strftime('%d/%m/%Y')
                        except ValueError:
                            formatted_date = task_date  # If conversion fails, use the original date

                        task_str = f"[{formatted_date}] {task_content}"
                    else:
                        task_str = task_content
                else:
                    task_str = task

                formatted_summary.append(f"• {task_str.strip()}")

        # Join all lines into a single string, with newlines between each
        return header + "\n".join(formatted_summary)


    

    def summarize_tasks_with_context(self, tasks):
        """Summarize tasks with context using T5 model."""
        if not tasks:
            return "No tasks found for today."

        channel_summaries = []
        for channel, contents in tasks.items():
            task_text = self.prioritize_tasks(", ".join(contents))
            if len(task_text.split()) < 5:
                channel_summaries.append(f"{channel}: \n {task_text}")
                continue

            contextual_input = f"Summarize the following tasks for {channel}: \n {task_text}"
            try:
                summary = self.summarize_or_answer_in_language(contextual_input)
                channel_summaries.append(f"{channel}: \n {summary}")
            except Exception as e:
                print(f"Error summarizing tasks for channel {channel}: \n{e}")
                channel_summaries.append(task_text)
        return "\n".join(channel_summaries)
    
    
    
    
    
    
