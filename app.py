# app.py

import gradio as gr
import pandas as pd
import textstat
import time
import itertools
import plotly.express as px # For visualizations

# Import our custom modules
from config import LLM_MODELS_FOR_TESTING, HEALTH_PROFILES
from llm_handler import get_ollama_response, get_ollama_response_non_stream

# --- Logging Setup ---
print("--- Local LLM Health Advisor ---")
print("Models available for testing:", list(LLM_MODELS_FOR_TESTING.keys()))
print("Scenarios available:", [p['scenario_name'] for p in HEALTH_PROFILES])
print("---------------------------------")

# --- Helper Function to build the prompt ---
def build_prompts(selected_profile):
    """Builds the system and user prompts for a given scenario."""
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
    user_prompt = f"""**Patient Context:**
- **Profile:** {selected_profile['profile_text']}
- **Primary Concern:** {selected_profile['target_disease_context']}
- **Key Information to Cover in Your Advice:** {', '.join(selected_profile['key_info_checklist'])}
- **Contextual Rules (for your information only, not for the user):** {selected_profile['simulated_rules']}

**User's Question:** "{selected_profile['user_question']}"
"""
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
    prompt_for_display = f"### System Prompt\n---\n{system_prompt}\n\n### User Prompt\n---\n{user_prompt}"
    return messages, prompt_for_display

# --- Single Evaluation Function (Streaming) ---
def generate_and_evaluate_stream(model_display_name, scenario_name, progress=gr.Progress(track_tqdm=True)):
    """
    Core streaming function for single evaluations.
    """
    if not model_display_name or not scenario_name:
        yield "Please select a model and a scenario.", "", "No stats.", ""
        return

    model_id = LLM_MODELS_FOR_TESTING[model_display_name]
    selected_profile = next((p for p in HEALTH_PROFILES if p['scenario_name'] == scenario_name), None)

    if not selected_profile:
        yield "Error: Profile not found.", "", "Error.", ""
        return

    messages, prompt_for_display = build_prompts(selected_profile)
    advice_stream = get_ollama_response(model_id, messages)
    
    profile_display = f"### {selected_profile['scenario_name']}\n**Profile:** {selected_profile['profile_text']}"
    
    start_time = time.time()
    advice_text = ""
    yield profile_display, "...", "Generating...", prompt_for_display

    for chunk in progress.tqdm(advice_stream, desc=f"Generating for {model_display_name}"):
        if "ERROR:" in chunk:
            advice_text = chunk
            yield profile_display, advice_text, "Error occurred.", prompt_for_display
            return
        advice_text += chunk
        yield profile_display, advice_text, "Generating...", prompt_for_display

    response_time = time.time() - start_time
    
    if "ERROR:" not in advice_text:
        flesch_score = textstat.flesch_reading_ease(advice_text)
        grade_level = textstat.flesch_kincaid_grade(advice_text)
        stats = (f"**Response Time:** {response_time:.2f}s\n"
                 f"**Readability (Flesch Ease):** {flesch_score:.1f}\n"
                 f"**Grade Level (FK):** {grade_level:.1f}")
    else:
        stats = f"Generation failed.\nTime: {response_time:.2f}s\n\n**Details:**\n{advice_text}"
        advice_text = "An error occurred. See 'Stats' box for details."
        
    yield profile_display, advice_text, stats, prompt_for_display

# --- Batch Evaluation Function (Non-Streaming) ---
def batch_evaluate(model_display_names, scenario_names, progress=gr.Progress(track_tqdm=True)):
    """
    Runs evaluation for all combinations of selected models and scenarios.
    """
    if not model_display_names or not scenario_names:
        # Return empty dataframe and a message
        return pd.DataFrame(), "Please select at least one model and one scenario.", gr.update(visible=False)

    results = []
    evaluation_pairs = list(itertools.product(model_display_names, scenario_names))
    
    for model_name, scenario_name in progress.tqdm(evaluation_pairs, desc="Running Batch Evaluation"):
        model_id = LLM_MODELS_FOR_TESTING[model_name]
        selected_profile = next((p for p in HEALTH_PROFILES if p['scenario_name'] == scenario_name), None)

        if not selected_profile:
            results.append({
                "Model": model_name, "Scenario": scenario_name, "Response Time (s)": 0,
                "Flesch Ease": None, "Flesch-Kincaid Grade": None, "Advice": "Scenario not found."
            })
            continue

        messages, _ = build_prompts(selected_profile)
        advice_text, response_time = get_ollama_response_non_stream(model_id, messages)

        if "ERROR:" not in advice_text and advice_text:
            flesch_score = textstat.flesch_reading_ease(advice_text)
            grade_level = textstat.flesch_kincaid_grade(advice_text)
        else:
            flesch_score, grade_level = None, None

        results.append({
            "Model": model_name,
            "Scenario": scenario_name,
            "Response Time (s)": float(f"{response_time:.2f}"),
            "Flesch Ease": float(f"{flesch_score:.1f}") if isinstance(flesch_score, (int, float)) else None,
            "Flesch-Kincaid Grade": float(f"{grade_level:.1f}") if isinstance(grade_level, (int, float)) else None,
            "Advice": advice_text
        })
    
    results_df = pd.DataFrame(results)
    # Return the dataframe, a success message, and make the visualization accordion visible
    return results_df, f"Batch evaluation complete. Ran {len(results_df)} tests.", gr.update(visible=True)

# --- Visualization Function ---
def update_visualizations(results_df):
    """Generates plots from the results DataFrame."""
    if results_df is None or results_df.empty:
        return None, None, None

    # Drop rows where metrics could not be calculated
    df_clean = results_df.dropna(subset=['Response Time (s)', 'Flesch Ease', 'Flesch-Kincaid Grade'])
    
    if df_clean.empty:
        return None, None, None
        
    # Plot 1: Response Time
    fig_time = px.bar(df_clean, x='Scenario', y='Response Time (s)', color='Model',
                      barmode='group', title='Response Time by Model and Scenario')
    
    # Plot 2: Flesch Reading Ease
    fig_ease = px.bar(df_clean, x='Scenario', y='Flesch Ease', color='Model',
                      barmode='group', title='Flesch Reading Ease by Model and Scenario')

    # Plot 3: Flesch-Kincaid Grade Level
    fig_grade = px.bar(df_clean, x='Scenario', y='Flesch-Kincaid Grade', color='Model',
                       barmode='group', title='Flesch-Kincaid Grade Level by Model and Scenario')

    return fig_time, fig_ease, fig_grade

# --- Gradio Interface Definition ---
with gr.Blocks(theme=gr.themes.Soft(), title="LLM Health Advisor") as demo:
    gr.Markdown("# Local LLM Health Advice Evaluator")
    gr.Markdown("Tool to test local Ollama models. Use the checkboxes for batch evaluation or dropdowns for a single, detailed run.")

    # --- Tabbed Interface ---
    with gr.Tabs():
        # --- Batch Comparison Tab ---
        with gr.TabItem("Batch Comparison"):
            with gr.Row():
                batch_model_select = gr.CheckboxGroup(choices=list(LLM_MODELS_FOR_TESTING.keys()), label="Select Models to Compare")
                batch_scenario_select = gr.CheckboxGroup(choices=[p['scenario_name'] for p in HEALTH_PROFILES], label="Select Scenarios to Test")
            
            with gr.Row():
                batch_run_btn = gr.Button("Run Batch Evaluation", variant="primary")
                cancel_btn = gr.Button("Cancel")
                
            batch_status_output = gr.Textbox(label="Batch Status", interactive=False)
            results_dataframe = gr.DataFrame(label="Batch Results", wrap=True)
            
            with gr.Accordion("Show Visualizations", open=False, visible=False) as viz_accordion:
                with gr.Row():
                    plot_time = gr.Plot(label="Response Time")
                with gr.Row():
                    plot_ease = gr.Plot(label="Reading Ease")
                with gr.Row():
                    plot_grade = gr.Plot(label="Grade Level")

            # Event handlers
            click_event = batch_run_btn.click(
                fn=batch_evaluate,
                inputs=[batch_model_select, batch_scenario_select],
                outputs=[results_dataframe, batch_status_output, viz_accordion]
            )
            
            # When the dataframe is updated, generate the plots
            results_dataframe.change(
                fn=update_visualizations,
                inputs=results_dataframe,
                outputs=[plot_time, plot_ease, plot_grade]
            )

            # Wire the cancel button
            cancel_btn.click(fn=None, inputs=None, outputs=None, cancels=[click_event])

        # --- Single Test / Streaming Tab ---
        with gr.TabItem("Single Model Test"):
            with gr.Row():
                single_model_select = gr.Dropdown(
                    choices=list(LLM_MODELS_FOR_TESTING.keys()),
                    label="Select LLM Model",
                    value=list(LLM_MODELS_FOR_TESTING.keys())[0] if LLM_MODELS_FOR_TESTING else None
                )
                single_scenario_select = gr.Dropdown(
                    choices=[p['scenario_name'] for p in HEALTH_PROFILES],
                    label="Select Health Scenario",
                    value=[p['scenario_name'] for p in HEALTH_PROFILES][0] if HEALTH_PROFILES else None
                )
            
            single_generate_btn = gr.Button("Generate Advice (Streaming)", variant="primary")
            
            with gr.Row():
                profile_output = gr.Markdown(label="Patient Profile")
                advice_output = gr.Markdown(label="Generated AI Advice") 
                stats_output = gr.Textbox(label="Performance & Stats", lines=5, interactive=False)
                
            with gr.Accordion("Show Full Prompt", open=False):
                prompt_output = gr.Markdown(label="Full Prompt Sent to LLM")

            single_generate_btn.click(
                fn=generate_and_evaluate_stream,
                inputs=[single_model_select, single_scenario_select],
                outputs=[profile_output, advice_output, stats_output, prompt_output]
            )

# This block ensures the app only runs when the script is executed directly
if __name__ == "__main__":
    demo.launch()