from typing import List, Dict, Optional
import os
import openai
import anthropic
from abc import ABC, abstractmethod
import asyncio
from dotenv import load_dotenv
import random

load_dotenv()

class AIModelGenerator(ABC):
    @abstractmethod
    async def generate_content(self, prompt: str, n: int) -> List[str]:
        pass

class OpenAIGenerator(AIModelGenerator):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
        openai.api_key = self.api_key
        
    async def generate_content(self, prompt: str, n: int) -> List[str]:
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a social media expert who creates engaging content."},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                n=n
            )
            return [choice.message.content for choice in response.choices]
        except Exception as e:
            print(f"OpenAI generation error: {str(e)}")
            return []

class ClaudeGenerator(AIModelGenerator):
    def __init__(self):
        self.client = anthropic.Client(api_key=os.getenv("CLAUDE_API_KEY"))
        self.model = os.getenv("CLAUDE_MODEL", "claude-2")
        self.temperature = float(os.getenv("CLAUDE_TEMPERATURE", "0.7"))
        
    async def generate_content(self, prompt: str, n: int) -> List[str]:
        try:
            responses = []
            for _ in range(n):
                response = await self.client.messages.create(
                    model=self.model,
                    messages=[{
                        "role": "user",
                        "content": prompt
                    }],
                    temperature=self.temperature
                )
                responses.append(response.content)
            return responses
        except Exception as e:
            print(f"Claude generation error: {str(e)}")
            return []

class MixedContentGenerator:
    def __init__(self):
        self.enabled_models = os.getenv("ENABLED_AI_MODELS", "openai,claude").split(",")
        self.variations_per_model = int(os.getenv("VARIATIONS_PER_MODEL", "2"))
        
        # Initialize weights
        self.weights = {
            "openai": float(os.getenv("OPENAI_WEIGHT", "0.6")),
            "claude": float(os.getenv("CLAUDE_WEIGHT", "0.4"))
        }
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        self.weights = {k: v/total_weight for k, v in self.weights.items()}
        
        # Initialize generators
        self.generators = {}
        if "openai" in self.enabled_models:
            self.generators["openai"] = OpenAIGenerator()
        if "claude" in self.enabled_models:
            self.generators["claude"] = ClaudeGenerator()
            
    async def generate_mixed_content(self, prompt: str) -> List[str]:
        """Generate content using multiple AI models and mix results based on weights"""
        all_content = []
        generation_tasks = []
        
        # Generate content from each enabled model
        for model_name, generator in self.generators.items():
            if model_name in self.enabled_models:
                task = generator.generate_content(
                    prompt=prompt,
                    n=self.variations_per_model
                )
                generation_tasks.append((model_name, task))
        
        # Wait for all generations to complete
        results = {}
        for model_name, task in generation_tasks:
            results[model_name] = await task
            
        # Mix content based on weights
        total_variations = sum(len(content) for content in results.values())
        mixed_content = []
        
        while len(mixed_content) < total_variations:
            # Choose model based on weights
            model = random.choices(
                list(self.weights.keys()),
                weights=[self.weights[m] for m in self.weights.keys()]
            )[0]
            
            # Add content if available
            if results[model]:
                content = results[model].pop(0)
                mixed_content.append({
                    "content": content,
                    "source_model": model
                })
                
        return mixed_content
    
    def get_enabled_models(self) -> List[Dict]:
        """Get information about enabled AI models"""
        return [
            {
                "name": model,
                "weight": self.weights.get(model, 0),
                "variations": self.variations_per_model
            }
            for model in self.enabled_models
        ]
