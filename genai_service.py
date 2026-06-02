"""
GenAI Service Integration Module
Parses VCAP_SERVICES for Tanzu GenAI service and provides chat API integration
"""
import os
import json
import requests
from typing import Optional, Dict, Iterator
from urllib.parse import urljoin


def get_genai_config() -> Optional[Dict[str, str]]:
    """
    Parse VCAP_SERVICES to extract GenAI service credentials.
    Returns GenAI configuration dict, or None if GenAI not configured.
    """
    vcap_services = os.environ.get('VCAP_SERVICES')
    if not vcap_services:
        return None
    
    try:
        services = json.loads(vcap_services)
        
        # Look for GenAI service - try multiple possible service types/names
        genai_service = None
        genai_service_types = ['genai', 'tanzu-genai', 'user-provided']
        
        for service_type in genai_service_types:
            if service_type in services and services[service_type]:
                # Check if any service matches GenAI pattern
                for service in services[service_type]:
                    service_name = service.get('name', '').lower()
                    # Look for GenAI service (could be chat, embeddings, etc.)
                    if 'genai' in service_type or 'genai' in service_name or 'chat' in service_name:
                        genai_service = service
                        break
                if genai_service:
                    break
        
        if not genai_service:
            return None
        
        creds = genai_service.get('credentials', {})
        
        # Extract GenAI credentials
        # Tanzu GenAI typically provides OpenAI-compatible API
        api_key = creds.get('api_key') or creds.get('apikey') or creds.get('apiKey')
        base_url = creds.get('base_url') or creds.get('baseUrl') or creds.get('url')
        model = creds.get('model') or creds.get('model_name') or 'gpt-4o-mini'  # default
        
        if not api_key:
            print("GenAI service found but missing API key")
            return None
        
        # Default to OpenAI-compatible endpoint if base_url not provided
        if not base_url:
            base_url = 'https://api.openai.com/v1'
        
        config = {
            'api_key': api_key,
            'base_url': base_url.rstrip('/'),
            'model': model
        }
        
        return config
        
    except Exception as e:
        print(f"Error parsing VCAP_SERVICES for GenAI: {e}")
        return None


def is_genai_configured() -> bool:
    """Check if GenAI is configured"""
    return get_genai_config() is not None


def chat_stream(message: str, system_prompt: str = None, context: str = None) -> Iterator[str]:
    """
    Stream chat response from GenAI service.
    Yields chunks of the response as they arrive.
    
    Args:
        message: User's chat message
        system_prompt: System prompt for the AI
        context: Additional context (e.g., album information)
    
    Yields:
        Response chunks as strings
    """
    config = get_genai_config()
    if not config:
        yield "Error: GenAI service not configured"
        return
    
    # Build messages for chat completion
    messages = []
    
    # Add system prompt if provided
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Add context if provided
    if context:
        user_message = f"Context:\n{context}\n\nUser Question: {message}"
    else:
        user_message = message
    
    messages.append({"role": "user", "content": user_message})
    
    # Prepare API request
    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": config['model'],
        "messages": messages,
        "stream": True,
        "temperature": 0.7
    }
    
    try:
        # Make streaming request
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=30)
        response.raise_for_status()
        
        # Parse SSE stream
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        choices = data.get('choices', [])
                        if choices:
                            delta = choices[0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
                        
    except requests.exceptions.RequestException as e:
        yield f"Error connecting to GenAI service: {str(e)}"
    except Exception as e:
        yield f"Error processing chat request: {str(e)}"


