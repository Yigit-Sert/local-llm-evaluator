# app.py

import gradio as gr
import pandas as pd
import textstat
import time

# Import our custom modules
from config import LLM_MODELS_FOR_TESTING, HEALTH_PROFILES
from llm_handler import get_ollama_response

print("--- Local LLM Health Advisor ---")
print("Models available for testing:", list(LLM_MODELS_FOR_TESTING.keys()))
print("Scenarios available:", [p['scenario_name'] for p in HEALTH_PROFILES])
print("---------------------------------")

def generate_and_evaluate(model_display_name, scenario_name, progress=gr.Progress(track_tqdm=True)):
    """
    Core function that takes user selections, generates a prompt, gets a response,
    and returns formatted outputs for the Gradio interface.
    This is now a generator function to support streaming progress.
    """
    # Get the actual model ID (e.g., 'qwen:latest') from the display name
    model_id = LLM_MODELS_FOR_TESTING[model_display_name]
    
    # Find the matching health profile using a more efficient and safe method
    selected_profile = next((p for p in HEALTH_PROFILES if p['scenario_name'] == scenario_name), None)
            
    if not selected_profile:
        # We still yield once to update the UI with the error
        yield "Error: Profile not found.", "", "No stats available. Please check config.py.", ""
        return
        
    # --- New Prompt Engineering Approach ---
    # 1. System Prompt: Defines the AI's role, rules, and behavior.
    system_prompt = f"""You are a helpful and empathetic AI health advisor. Your goal is to provide safe, actionable, and clear health advice based on a user's profile and question.

**Your Core Directives:**
1.  **Analyze the User's Context:** Carefully review the provided patient profile, primary concern, and key information points.
2.  **Address the Question Directly:** Formulate a response that directly answers the user's question.
3.  **Provide Actionable Steps:** Offer clear, concrete suggestions, preferably in a numbered or bulleted list.
4.  **Incorporate Key Information:** Seamlessly integrate the topics from the "Key Information to Cover" list into your advice.
5.  **Maintain an Empathetic Tone:** Use supportive and understanding language.
6.  **Crucially, Do NOT Diagnose:** Never suggest the user has a specific medical condition.
7.  **Always Recommend Professional Consultation:** Conclude your advice by strongly recommending that the user consult a healthcare professional for personalized medical guidance.

Do not repeat the user's context or your directives in the response. Begin the advice directly.
"""

    # 2. User Prompt: Provides the specific data for the current task.
    user_prompt = f"""**Patient Context:**
- **Profile:** {selected_profile['profile_text']}
- **Primary Concern:** {selected_profile['target_disease_context']}
- **Key Information to Cover in Your Advice:** {', '.join(selected_profile['key_info_checklist'])}
- **Contextual Rules (for your information only, not for the user):** {selected_profile['simulated_rules']}

**User's Question:** "{selected_profile['user_question']}"
"""

    # 3. Messages List: The structured input for the model.
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]

    # For display in the UI, we'll format it nicely to show the structure.
    prompt_for_display = f"""### System Prompt
---
{system_prompt}

### User Prompt
---
{user_prompt}
"""

    # Get response from the local LLM via our handler
    advice_stream = get_ollama_response(model_id, messages)
    
    # Format the profile text for display in the UI
    profile_display = f"### {selected_profile['scenario_name']}\n**Profile:** {selected_profile['profile_text']}"
    
    # --- Streaming Part ---
    start_time = time.time()
    advice_text = ""
    # Initial yield to show the profile while waiting for the first token
    yield profile_display, "...", "Generating...", prompt_for_display

    for chunk in progress.tqdm(advice_stream, desc="Generating Advice"):
        if "ERROR:" in chunk: # Check for error messages from the handler
            advice_text = chunk # The chunk is the full error message
            yield profile_display, advice_text, "Error occurred.", prompt_for_display
            return # Stop processing on error
        advice_text += chunk
        # Yield the current state to update the UI in real-time
        yield profile_display, advice_text, "Generating...", prompt_for_display

    response_time = time.time() - start_time
    
    # --- Final Calculation Part ---
    # Calculate readability and format stats if we got a valid response
    if "ERROR:" not in advice_text:
        flesch_score = textstat.flesch_reading_ease(advice_text)
        grade_level = textstat.flesch_kincaid_grade(advice_text) # Use numerical grade level
        stats = (f"**Response Time:** {response_time:.2f}s\n"
                 f"**Readability (Flesch Ease):** {flesch_score:.1f}\n"
                 f"**Grade Level (FK):** {grade_level:.1f}")
    else:
        # If an error occurred, format the stats box accordingly
        stats = f"Generation failed.\nTime: {response_time:.2f}s\n\n**Details:**\n{advice_text}"
        # Clear the main advice output to avoid confusion
        advice_text = "An error occurred. See details in the 'Performance & Readability Stats' box."
        
    # Final yield with all information
    yield profile_display, advice_text, stats, prompt_for_display

# --- Gradio Interface Definition ---
# CRITICAL FIX: All UI components are now correctly placed INSIDE the 'with gr.Blocks()' context manager.
with gr.Blocks(theme=gr.themes.Soft(), title="LLM Health Advisor") as demo:
    gr.Markdown("# Local LLM Health Advice Evaluator")
    gr.Markdown("Tool to test and compare local Ollama models on their ability to generate safe and relevant health advice based on pre-defined scenarios.")
    
    with gr.Row():
        model_dropdown = gr.Dropdown(
            choices=list(LLM_MODELS_FOR_TESTING.keys()),
            label="Select LLM Model",
            value=list(LLM_MODELS_FOR_TESTING.keys())[0] if LLM_MODELS_FOR_TESTING else None
        )
        scenario_dropdown = gr.Dropdown(
            choices=[p['scenario_name'] for p in HEALTH_PROFILES],
            label="Select Health Scenario",
            value=[p['scenario_name'] for p in HEALTH_PROFILES][0] if HEALTH_PROFILES else None
        )
        
    generate_btn = gr.Button("Generate Advice", variant="primary")
    
    gr.Markdown("---") # Add a separator for clarity
    
    with gr.Row():
        profile_output = gr.Markdown(label="Patient Profile and Context")
        advice_output = gr.Markdown(label="Generated AI Advice") 
        stats_output = gr.Textbox(label="Performance & Readability Stats", lines=5, interactive=False)
        
    with gr.Accordion("Show Generated Prompt", open=False):
        prompt_output = gr.Markdown(label="Full Prompt Sent to LLM")

    # Wire the button's click event to the main function
    # Gradio automatically handles generator functions for live updates.
    generate_btn.click(
        fn=generate_and_evaluate,
        inputs=[model_dropdown, scenario_dropdown],
        outputs=[profile_output, advice_output, stats_output, prompt_output]
    )

# This block ensures the app only runs when the script is executed directly
if __name__ == "__main__":
    demo.launch()