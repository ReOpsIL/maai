import logging
import os
import requests
from utils import load_config
from agents.ai_client import AiClient
from openai import OpenAI

class OpenAIClient(AiClient):

    def __init__(self):
        """
        Initializes the ai model client api.
        """

        self.logger = logging.getLogger(self.__class__.__name__)

        # Load configuration
        config = load_config()
        self.model_name = config.get('llm', {}).get('model')
        self.provider = config.get('llm', {}).get('provider')
        self.reasoning_effort = config.get('llm', {}).get('reasoning_effort')
        self.temperature = config.get('llm', {}).get('temperature')

        self.logger.info(f"Using LLM - Provider: {self.provider}, Model: {self.model_name}, Reasoning effort: {self.reasoning_effort}")

        # Configure xAI API (ensure XAI_API_KEY is set in the environment)
        try:
            if "grok" in self.provider:
                self.api_key = os.environ.get("XAI_API_KEY")
                self.base_url="https://api.x.ai/v1"
            elif "groq" in self.provider:
                self.api_key = os.environ.get("GROQ_API_KEY")
                self.base_url="https://api.groq.com/openai/v1"
            elif "openrouter" in self.provider:
                self.api_key = os.environ.get("OPENROUTER_API_KEY")
                self.base_url="https://openrouter.ai/api/v1"

            self.model = OpenAI( api_key=self.api_key, base_url=self.base_url)

        except ValueError as e:
            self.logger.error(f"API Key Configuration Error: {e}")
            raise Exception("FATAL error - Stopping!")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during API configuration: {e}")
            raise Exception("FATAL error - Stopping!")

        self.logger.info(f"{self.provider} initialized for model: {self.model_name}")


    def generate_content(self, prompt: str) -> str:
        if self.model is None:
            self.logger.error("Model not initialized. Cannot generate response.")
            return ""

        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        print(prompt)
        print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@\n")
        
        try:
            messages=[
                #{"role": "system", "content": "You are a highly intelligent AI assistant."},
                {"role": "user", "content": prompt}
            ]
            if self.reasoning_effort == "none":
                 completion = self.model.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature = self.temperature
                )
            else:
                completion = self.client.chat.completions.create(
                    model=self.model_name,
                    reasoning_effort=self.reasoning_effort,
                    messages=messages,
                    temperature=self.temperature,
                )

            if completion.choices is None:
                raise Exception(str(completion.error))

            print(completion.choices)
            return completion.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error generating response from model API: {e}")
            raise Exception("FATAL error - Stopping!")
