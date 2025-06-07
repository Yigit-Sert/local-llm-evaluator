# llm_handler.py

import ollama
import time

def get_ollama_response(model_name: str, messages: list):
    """
    Gets a streaming response from an Ollama model. This is a generator.

    Args:
        model_name: The name of the Ollama model to use (e.g., 'qwen:latest').
        messages: The list of messages (with roles) to send to the model.

    Yields:
        str: The next chunk of the generated text response or an error message.
    """
    try:
        stream = ollama.chat(
            model=model_name,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                yield chunk['message']['content']
            elif 'error' in chunk:
                # This handles model not found errors during streaming
                error_message = f"ERROR: Ollama stream error for model '{model_name}'.\nDetails: {chunk['error']}"
                print(error_message)
                yield error_message
                return

    except ollama.ResponseError as e:
        # This handles errors from the Ollama server itself, e.g., "model not found"
        error_message = f"ERROR: Ollama response error for model '{model_name}'.\nDetails: {e.error}"
        print(error_message) # Also print to console for debugging
        yield error_message
        
    except Exception as e:
        # This catches other exceptions, like connection errors if the server isn't running
        error_message = f"ERROR: Could not connect to the Ollama server. Please ensure it is running.\nDetails: {e}"
        print(error_message) # Also print to console for debugging
        yield error_message