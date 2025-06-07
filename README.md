# Local LLM Health Advisor Evaluator

This project provides a simple web interface using Gradio to evaluate and compare the performance of different local language models (LLMs) running via Ollama. It is specifically designed to test their ability to generate safe, empathetic, and relevant health advice based on a series of pre-defined patient scenarios.

## Features

-   **Side-by-Side Model Comparison**: Easily select from a list of your installed Ollama models to test.
-   **Scenario-Based Testing**: Comes with pre-built health profiles and user questions to ensure consistent evaluation.
-   **Advanced Prompt Engineering**: Uses a system/user prompt structure to guide the AI's behavior and improve response quality.
-   **Real-time Streaming**: Displays the AI's advice as it's being generated.
-   **Performance Metrics**: Automatically calculates and displays the response time and readability scores (Flesch Reading Ease, Flesch-Kincaid Grade Level) for each generated response.
-   **Prompt Visibility**: Includes an accordion to view the exact, full prompt sent to the model for better debugging and analysis.
-   **Easy Configuration**: Models and scenarios can be easily added or modified by editing the `config.py` file.

## How It Works

1.  **Backend**: A Python script using the `ollama` library to connect to a running Ollama instance.
2.  **Frontend**: A Gradio web interface (`app.py`) that provides dropdowns for model and scenario selection.
3.  **Configuration**: A central `config.py` file holds the list of models to test and the detailed health scenarios.
4.  **Prompting**: When a user clicks "Generate Advice", the application constructs a detailed two-part prompt:
    *   A **System Prompt** gives the AI its core instructions (be empathetic, don't diagnose, etc.).
    *   A **User Prompt** provides the specific patient profile and question for the current scenario.
5.  **Evaluation**: The generated text is analyzed using the `textstat` library to provide readability metrics.

## Setup and Installation

1.  **Install Ollama**: You must have [Ollama](https://ollama.ai/) installed and running on your machine.

2.  **Download LLMs**: Pull the models you want to test from the Ollama library. For example:
    ```bash
    ollama pull qwen:latest
    ollama pull llama3:8b
    ```

3.  **Clone the Repository**:
    ```bash
    git clone https://github.com/Yigit-Sert/local-llm-evaluator.git
    cd local-llm-evaluator
    ```

4.  **Install Python Dependencies**: It's recommended to use a virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

5.  **Configure Models**: Open `config.py` and update the `LLM_MODELS_FOR_TESTING` dictionary to match the models you have downloaded. The key is the display name, and the value is the exact model tag used by Ollama.

    ```python
    # config.py
    LLM_MODELS_FOR_TESTING = {
        "Qwen (Latest Version)": "qwen:latest",
        "Llama 3 8B": "llama3:8b",
        # Add other models here
    }
    ```

## How to Run

1.  **Ensure Ollama is Running**: Make sure the Ollama application or server process is active.

2.  **Start the Gradio App**:
    ```bash
    python3 app.py
    ```

3.  Open your web browser and navigate to the local URL provided by Gradio (usually `http://127.0.0.1:7860`).

4.  Use the dropdown menus to select a model and a scenario, then click "Generate Advice". 