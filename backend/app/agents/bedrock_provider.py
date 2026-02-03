"""
AWS Bedrock LLM Provider for iRecover Agents

Provides abstraction layer for AWS Bedrock API
with support for Claude, Llama, and other models.
"""
import json
import structlog
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
import asyncio

from app.config import settings

logger = structlog.get_logger()


class BedrockProvider:
    """
    AWS Bedrock API provider for agents.
    Handles all interactions with AWS Bedrock API.
    """
    
    def __init__(self):
        """Initialize Bedrock provider with AWS credentials from settings."""
        if not settings.aws_access_key_id or not settings.aws_secret_access_key:
            raise ValueError("AWS credentials not configured in environment")
        
        self.model_id = settings.bedrock_model_id
        self.temperature = settings.bedrock_temperature
        self.region = settings.aws_region
        self.max_tokens = settings.bedrock_max_tokens
        
        # Initialize boto3 client
        import boto3
        
        client_kwargs = {
            'service_name': 'bedrock-runtime',
            'region_name': self.region,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key
        }
        
        # Add session token if provided (for temporary credentials)
        if settings.aws_session_token:
            client_kwargs['aws_session_token'] = settings.aws_session_token
        
        self.client = boto3.client(**client_kwargs)
        
        logger.info(
            "Initialized Bedrock provider",
            model=self.model_id,
            region=self.region
        )
    
    def _format_messages_for_claude(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> tuple[str, List[Dict[str, Any]]]:
        """
        Format messages for Claude models (Anthropic format).
        
        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: System prompt for the model
            
        Returns:
            Tuple of (system_prompt, formatted_messages)
        """
        formatted_messages = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            # Map OpenAI roles to Claude roles
            if role == "assistant":
                formatted_messages.append({
                    "role": "assistant",
                    "content": content
                })
            elif role == "user":
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
            # Skip system messages as they're handled separately
        
        return system_prompt or "", formatted_messages
    
    def _format_messages_for_llama(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Format messages for Llama models.
        
        Args:
            messages: List of message dicts
            system_prompt: System prompt
            
        Returns:
            Formatted prompt string
        """
        prompt_parts = []
        
        if system_prompt:
            prompt_parts.append(f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n")
        else:
            prompt_parts.append("<s>[INST] ")
        
        for i, msg in enumerate(messages):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "user":
                if i == 0:
                    prompt_parts.append(f"{content} [/INST]")
                else:
                    prompt_parts.append(f"<s>[INST] {content} [/INST]")
            elif role == "assistant":
                prompt_parts.append(f" {content} </s>")
        
        return "".join(prompt_parts)
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Generate text response from Bedrock model.
        
        Args:
            messages: List of message dicts with "role" and "content"
            system_prompt: System prompt for the model
            tools: Optional tool definitions (not yet supported)
            temperature: Optional temperature override
            
        Returns:
            Generated text response
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            
            # Determine model family from model_id
            is_claude = "claude" in self.model_id.lower()
            is_llama = "llama" in self.model_id.lower()
            is_titan = "titan" in self.model_id.lower()
            
            # Format request based on model
            if is_claude:
                system, formatted_messages = self._format_messages_for_claude(messages, system_prompt)
                
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": temp,
                    "messages": formatted_messages
                }
                
                if system:
                    body["system"] = system
                
            elif is_llama:
                prompt = self._format_messages_for_llama(messages, system_prompt)
                
                body = {
                    "prompt": prompt,
                    "max_gen_len": self.max_tokens,
                    "temperature": temp,
                    "top_p": 0.9
                }
                
            elif is_titan:
                # Combine all messages into a single prompt for Titan
                prompt_parts = []
                if system_prompt:
                    prompt_parts.append(f"System: {system_prompt}\n\n")
                
                for msg in messages:
                    role = msg.get("role", "user").title()
                    content = msg.get("content", "")
                    prompt_parts.append(f"{role}: {content}\n")
                
                body = {
                    "inputText": "".join(prompt_parts),
                    "textGenerationConfig": {
                        "maxTokenCount": self.max_tokens,
                        "temperature": temp,
                        "topP": 0.9
                    }
                }
            else:
                # Generic format for other models
                prompt_parts = []
                if system_prompt:
                    prompt_parts.append(f"System: {system_prompt}\n\n")
                
                for msg in messages:
                    role = msg.get("role", "user").title()
                    content = msg.get("content", "")
                    prompt_parts.append(f"{role}: {content}\n")
                
                body = {
                    "prompt": "".join(prompt_parts),
                    "max_tokens": self.max_tokens,
                    "temperature": temp
                }
            
            # Call Bedrock API using asyncio
            response = await asyncio.to_thread(
                self.client.invoke_model,
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            # Extract text based on model
            if is_claude:
                text = response_body['content'][0]['text']
            elif is_llama:
                text = response_body.get('generation', '')
            elif is_titan:
                text = response_body['results'][0]['outputText']
            else:
                # Try common response formats
                text = (response_body.get('completion') or 
                       response_body.get('generation') or 
                       response_body.get('output') or
                       str(response_body))
            
            logger.info(
                "Bedrock text generation completed",
                model=self.model_id,
                input_messages=len(messages),
                output_length=len(text),
            )
            
            return text
        
        except Exception as e:
            logger.error("Error calling Bedrock API", error=str(e), model=self.model_id)
            raise
    
    async def stream_text(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream text response from Bedrock model.
        
        Args:
            messages: List of message dicts
            system_prompt: System prompt
            temperature: Optional temperature override
            
        Yields:
            Text chunks from the response
        """
        try:
            temp = temperature if temperature is not None else self.temperature
            
            # Determine model family
            is_claude = "claude" in self.model_id.lower()
            
            if is_claude:
                system, formatted_messages = self._format_messages_for_claude(messages, system_prompt)
                
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": self.max_tokens,
                    "temperature": temp,
                    "messages": formatted_messages
                }
                
                if system:
                    body["system"] = system
            else:
                # For non-Claude models, streaming might not be supported
                # Fall back to non-streaming
                text = await self.generate_text(messages, system_prompt, temperature=temperature)
                yield text
                return
            
            # Stream response
            response = await asyncio.to_thread(
                self.client.invoke_model_with_response_stream,
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            stream = response.get('body')
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_data = json.loads(chunk.get('bytes').decode())
                        
                        if chunk_data.get('type') == 'content_block_delta':
                            delta = chunk_data.get('delta', {})
                            if delta.get('type') == 'text_delta':
                                text = delta.get('text', '')
                                if text:
                                    yield text
        
        except Exception as e:
            logger.error("Error streaming from Bedrock", error=str(e))
            raise
    
    async def analyze_json(
        self,
        data: Dict[str, Any],
        analysis_prompt: str,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze JSON data with Bedrock and return structured JSON response.
        
        Args:
            data: JSON data to analyze
            analysis_prompt: Prompt describing the analysis
            system_prompt: Optional system context
            
        Returns:
            Parsed JSON response from model
        """
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
            # Extract JSON from response (handle markdown code blocks)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            result = json.loads(response_text)
            logger.info("JSON analysis completed", analysis_prompt=analysis_prompt[:50])
            return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON response from Bedrock", response=response_text[:100])
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
            # Handle markdown code blocks
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
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
            # Handle markdown code blocks
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
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
_bedrock_provider: Optional[BedrockProvider] = None


def get_bedrock_provider() -> BedrockProvider:
    """
    Get or create the global Bedrock provider instance.
    
    Returns:
        BedrockProvider instance
    """
    global _bedrock_provider
    if _bedrock_provider is None:
        _bedrock_provider = BedrockProvider()
    return _bedrock_provider
