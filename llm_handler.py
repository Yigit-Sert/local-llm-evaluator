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


def get_ollama_response_non_stream(model_name: str, messages: list) -> (str, float):
    """
    Gets a single, complete response from an Ollama model and the response time.

    Args:
        model_name: The name of the Ollama model to use.
        messages: The list of messages to send.

    Returns:
        A tuple containing the full response text (or error) and the response time.
    """
    advice_text = ""
    start_time = time.time()
    try:
        response = ollama.chat(
            model=model_name,
            messages=messages,
            stream=False, # The only change needed for a non-streaming call
        )
        if 'message' in response and 'content' in response['message']:
            advice_text = response['message']['content']
        elif 'error' in response:
            advice_text = f"ERROR: Ollama error for model '{model_name}'. Details: {response['error']}"
        else:
            advice_text = "ERROR: Unknown response format from Ollama."

    except ollama.ResponseError as e:
        advice_text = f"ERROR: Ollama response error for model '{model_name}'. Details: {e.error}"
    except Exception as e:
        advice_text = f"ERROR: Could not connect to the Ollama server. Details: {e}"

    response_time = time.time() - start_time
    print(f"Non-stream response for {model_name} took {response_time:.2f}s") # For debugging
    return advice_text, response_time