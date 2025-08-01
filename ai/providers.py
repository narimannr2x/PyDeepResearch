from dotenv import load_dotenv
import os
import asyncio
from openai import OpenAI
from .text_splitter import RecursiveCharacterTextSplitter
import tiktoken


# Load environment variables
load_dotenv()
# Initialize OpenAI client
client = OpenAI()


encoder  = tiktoken.get_encoding("o200k_base")
MinChunkSize = 140

def get_model():
    
    return "gpt-4.1-nano"

def generate_structured_response(prompt: str, system_prompt: str, model: str, format_schema) :
    """Synchronous OpenAI call."""
    resp = client.responses.parse( # type: ignore
        model=model,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        text_format=format_schema,
    )
    return resp

async def generate_structured_response_async(prompt: str, system_prompt: str, model: str, format_schema) :
    """Async wrapper around the same call, suitable for asyncio."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, generate_structured_response, prompt, system_prompt, model, format_schema)

def trim_prompt(prompt, context_size=None):
    """Trim prompt to fit within context size"""
    if context_size is None:
        context_size = int(os.getenv("CONTEXT_SIZE", "128000"))
    
    if not prompt:
        return ""
    
    # Check if prompt is already within context size
    token_count = len(encoder.encode(prompt))
    if token_count <= context_size:
        return prompt
    
    # Calculate overflow and estimate character reduction
    overflow_tokens = token_count - context_size
    estimated_chars_to_remove = overflow_tokens * 3  # Rough estimate: 3 chars per token
    chunk_size = max(len(prompt) - estimated_chars_to_remove, MinChunkSize)
    
    # Use text splitter to trim
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=0
    )
    chunks = splitter.split_text(prompt)
    trimmed = chunks[0] if chunks else ""
    
    # Handle edge case where trimming didn't reduce size
    if len(trimmed) == len(prompt):
        return prompt[:chunk_size]
    
    # Recursively trim if still too long
    return trim_prompt(trimmed, context_size)