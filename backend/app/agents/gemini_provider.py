"""
Gemini LLM Provider for iRecover Agents

Provides abstraction layer for Google's Generative AI (Gemini) API
with streaming support, tool integration, and observability via REST API.
"""
import json
import structlog
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import asyncio

# Don't import genai SDK - use REST API for Python 3.14 compatibility
# import google.generativeai as genai
# from google.api_core.exceptions import GoogleAPIError

from app.config import settings

logger = structlog.get_logger()


class GeminiProvider:
    """
    Gemini API provider for agents.
    Handles all interactions with Google's Generative AI API via REST.
    """
    
    def __init__(self):
        """Initialize Gemini provider with API key from settings."""
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not configured in environment")
        
        # Don't initialize genai SDK - use REST API directly for Python 3.14 compatibility
        self.model_name = settings.gemini_model
        self.temperature = settings.gemini_temperature
        self.api_key = settings.gemini_api_key
        
        logger.info(f"Initialized Gemini provider with model: {self.model_name} (REST API mode)")
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text response from Gemini model using REST API.
        
        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: System prompt for the model
            tools: Optional tool definitions
            temperature: Optional temperature override
            
        Returns:
            Generated text response
        """
        try:
            import aiohttp
            
            temp = temperature if temperature is not None else self.temperature
            
            # Build the prompt
            prompt_parts = []
            if system_prompt:
                prompt_parts.append(f"SYSTEM: {system_prompt}\n\n")
            
            for msg in messages:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                prompt_parts.append(f"{role}: {content}\n")
            
            full_prompt = "".join(prompt_parts)
            
            # Use REST API directly (Python 3.14 compatible)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": full_prompt}]
                }],
                "generationConfig": {
                    "temperature": temp,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 2048,
                }
            }
            
            import ssl
            # Create SSL context that doesn't verify certificates (for development)
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Gemini API error: {response.status} - {error_text}")
                        raise Exception(f"Gemini API returned {response.status}: {error_text}")
                    
                    result = await response.json()
                    text = result["candidates"][0]["content"]["parts"][0]["text"]
            
            logger.info(
                "Gemini text generation completed",
                model=self.model_name,
                input_messages=len(messages),
                output_length=len(text),
            )
            
            return text
        
        except Exception as e:
            logger.error("Error calling Gemini API", error=str(e))
            raise
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text response from Gemini model.
        
        Args:
            messages: List of message dicts
            system_prompt: System prompt
            temperature: Optional temperature override
            
        Yields:
            Text chunks from the response
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            contents = self._prepare_contents(messages, system_prompt)
            
            # Use asyncio to run blocking stream operation
            response = await asyncio.to_thread(
                self.model.generate_content,
                contents,
                generation_config=genai.types.GenerationConfig(
                    temperature=temp,
                    max_output_tokens=2048,
                ),
                stream=True,
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        
        except GoogleAPIError as e:
            logger.error("Gemini streaming API error", error=str(e))
            raise
        except Exception as e:
            logger.error("Error streaming from Gemini", error=str(e))
            raise
    
    def _prepare_contents(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Convert OpenAI message format to Gemini format.
        
        Gemini expects:
        - "user" role for user messages
        - "model" role for assistant messages
        - System prompt as first message or in system_instruction
        
        Args:
            messages: OpenAI format messages
            system_prompt: Optional system prompt
            
        Returns:
            Gemini format contents
        """
        contents = []
        
        # Add system prompt as first user message if provided
        if system_prompt:
            contents.append({
                "role": "user",
                "parts": [system_prompt]
            })
            contents.append({
                "role": "model",
                "parts": ["I understand. I will follow these instructions."]
            })
        
        # Convert messages
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Map OpenAI roles to Gemini roles
            if role == "assistant":
                role = "model"
            elif role == "system":
                continue  # System messages are handled above
            
            contents.append({
                "role": role,
                "parts": [content]
            })
        
        return contents
    
    async def analyze_json(
        self,
        data: Dict[str, Any],
        analysis_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze JSON data with Gemini and return structured JSON response.
        
        Args:
            data: JSON data to analyze
            analysis_prompt: Prompt describing the analysis
            system_prompt: Optional system context
            
        Returns:
            Parsed JSON response from model
        """
        # Prepare the prompt with JSON data
        full_prompt = f"""Analyze the following data and respond with valid JSON only, no additional text:

Data to analyze:
{json.dumps(data, indent=2)}

Analysis task:
{analysis_prompt}

Respond with valid JSON only."""
        
        messages = [
            {"role": "user", "content": full_prompt}
        ]
        
        response_text = await self.generate_text(messages, system_prompt)
        
        try:
            # Extract JSON from response
            result = json.loads(response_text)
            logger.info("JSON analysis completed", analysis_prompt=analysis_prompt[:50])
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from Gemini", response=response_text[:100])
            # Return the response as-is if not JSON
            return {"raw_response": response_text}
    
    async def extract_entities(
        self,
        text: str,
        entity_types: List[str],
    ) -> Dict[str, List[str]]:
        """
        Extract entities of specified types from text.
        
        Args:
            text: Text to analyze
            entity_types: Types of entities to extract
            
        Returns:
            Dictionary mapping entity type to list of entities
        """
        system_prompt = f"""You are an entity extraction specialist. Extract {', '.join(entity_types)} from the provided text.
Respond with ONLY valid JSON in this format:
{{"entities": {{{{{', '.join(f'"{t}": []' for t in entity_types)}}}}}}}"""
        
        messages = [
            {"role": "user", "content": f"Extract entities from: {text}"}
        ]
        
        response_text = await self.generate_text(messages, system_prompt)
        
        try:
            result = json.loads(response_text)
            return result.get("entities", {})
        except json.JSONDecodeError:
            logger.warning("Failed to parse entity extraction response")
            return {entity_type: [] for entity_type in entity_types}
    
    async def classify_text(
        self,
        text: str,
        categories: List[str],
    ) -> Dict[str, Any]:
        """
        Classify text into one of the provided categories.
        
        Args:
            text: Text to classify
            categories: List of possible categories
            
        Returns:
            Classification result with category and confidence
        """
        system_prompt = f"""Classify the following text into one of these categories: {', '.join(categories)}.
Respond with ONLY valid JSON in this format:
{{"category": "string", "confidence": 0.0, "reasoning": "string"}}"""
        
        messages = [
            {"role": "user", "content": f"Classify: {text}"}
        ]
        
        response_text = await self.generate_text(messages, system_prompt)
        
        try:
            result = json.loads(response_text)
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse classification response")
            return {
                "category": categories[0] if categories else "unknown",
                "confidence": 0.5,
                "reasoning": "Classification failed"
            }


# Global provider instance
_gemini_provider: Optional[GeminiProvider] = None


def get_gemini_provider() -> GeminiProvider:
    """
    Get or create the global Gemini provider instance.
    
    Returns:
        GeminiProvider instance
    """
    global _gemini_provider
    if _gemini_provider is None:
        _gemini_provider = GeminiProvider()
    return _gemini_provider
