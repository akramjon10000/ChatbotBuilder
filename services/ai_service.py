import os
import logging
import time
from google import genai
from google.genai import types

class AIService:
    def __init__(self):
        """Initialize AI service with Gemini API"""
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.model = "gemini-2.5-flash"
        
    def generate_response(self, user_message, system_prompt=None, language='uz', conversation_id=None):
        """Generate AI response using Gemini"""
        try:
            # Prepare system instruction based on language
            language_instructions = {
                'uz': "Siz O'zbek tilida javob beradigan yordamchi botsiz. Har doim O'zbek tilida javob bering.",
                'ru': "Вы помощник-бот, отвечающий на русском языке. Всегда отвечайте на русском языке.",
                'en': "You are an assistant bot that responds in English. Always respond in English."
            }
            
            base_instruction = language_instructions.get(language, language_instructions['uz'])
            
            if system_prompt:
                system_instruction = f"{base_instruction}\n\nQo'shimcha ko'rsatmalar: {system_prompt}"
            else:
                system_instruction = base_instruction
            
            # Generate response
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Content(role="user", parts=[types.Part(text=user_message)])
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )
            
            if response.text:
                return response.text
            else:
                return self._get_fallback_response(language)
                
        except Exception as e:
            logging.error(f"AI service error: {e}")
            return self._get_fallback_response(language)
    
    def generate_response_with_context(self, user_message, conversation_history, system_prompt=None, language='uz'):
        """Generate AI response with conversation context"""
        try:
            # Prepare conversation history
            contents = []
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                role = "user" if msg.is_from_user else "model"
                contents.append(
                    types.Content(role=role, parts=[types.Part(text=msg.content)])
                )
            
            # Add current message
            contents.append(
                types.Content(role="user", parts=[types.Part(text=user_message)])
            )
            
            # Prepare system instruction
            language_instructions = {
                'uz': "Siz O'zbek tilida javob beradigan yordamchi botsiz. Har doim O'zbek tilida javob bering.",
                'ru': "Вы помощник-бот, отвечающий на русском языке. Всегда отвечайте на русском языке.",
                'en': "You are an assistant bot that responds in English. Always respond in English."
            }
            
            base_instruction = language_instructions.get(language, language_instructions['uz'])
            
            if system_prompt:
                system_instruction = f"{base_instruction}\n\nQo'shimcha ko'rsatmalar: {system_prompt}"
            else:
                system_instruction = base_instruction
            
            # Generate response
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=1000
                )
            )
            
            if response.text:
                return response.text
            else:
                return self._get_fallback_response(language)
                
        except Exception as e:
            logging.error(f"AI service with context error: {e}")
            return self._get_fallback_response(language)
    
    def analyze_image(self, image_path, user_message=None, language='uz'):
        """Analyze image using Gemini Vision"""
        try:
            with open(image_path, "rb") as f:
                image_bytes = f.read()
            
            # Prepare prompt based on language
            prompts = {
                'uz': "Bu rasmni tahlil qiling va O'zbek tilida tushuntiring:",
                'ru': "Проанализируйте это изображение и объясните на русском языке:",
                'en': "Analyze this image and explain in English:"
            }
            
            prompt = prompts.get(language, prompts['uz'])
            if user_message:
                prompt += f" {user_message}"
            
            response = self.client.models.generate_content(
                model="gemini-2.5-pro",
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type="image/jpeg"
                    ),
                    prompt
                ]
            )
            
            if response.text:
                return response.text
            else:
                return self._get_fallback_response(language)
                
        except Exception as e:
            logging.error(f"Image analysis error: {e}")
            return self._get_fallback_response(language)
    
    def summarize_text(self, text, language='uz'):
        """Summarize text using Gemini"""
        try:
            prompts = {
                'uz': f"Quyidagi matnni O'zbek tilida qisqacha mazmunlang:\n\n{text}",
                'ru': f"Кратко изложите следующий текст на русском языке:\n\n{text}",
                'en': f"Summarize the following text in English:\n\n{text}"
            }
            
            prompt = prompts.get(language, prompts['uz'])
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            
            if response.text:
                return response.text
            else:
                return self._get_fallback_response(language)
                
        except Exception as e:
            logging.error(f"Text summarization error: {e}")
            return self._get_fallback_response(language)
    
    def _get_fallback_response(self, language):
        """Get fallback response when AI fails"""
        responses = {
            'uz': "Kechirasiz, hozir javob bera olmayman. Iltimos, keyinroq urinib ko'ring.",
            'ru': "Извините, я не могу ответить прямо сейчас. Пожалуйста, попробуйте позже.",
            'en': "Sorry, I can't respond right now. Please try again later."
        }
        return responses.get(language, responses['uz'])
    
    def detect_language(self, text):
        """Detect language of the text"""
        try:
            # Simple language detection based on character patterns
            if any(char in text for char in "ёъ"):
                return 'ru'
            elif any(ord(char) > 127 for char in text):
                return 'uz'
            else:
                return 'en'
        except:
            return 'uz'  # Default to Uzbek
