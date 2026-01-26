import os
import random
import time
from locust import HttpUser, task, between, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
JWT_TOKEN = os.getenv("SUNA_JWT_TOKEN")
if not JWT_TOKEN:
    print("WARNING: SUNA_JWT_TOKEN env var not set. Requests may fail if auth is required.")

def get_test_prompt():
    """
    Get the test prompt from environment variables or file.
    Priority:
    1. SUNA_TEST_PROMPT_FILE (reads content from file)
    2. SUNA_TEST_PROMPT (raw string)
    3. Default fallback string
    """
    prompt_file = os.getenv("SUNA_TEST_PROMPT_FILE")
    if prompt_file:
        if os.path.exists(prompt_file):
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        print(f"Loaded prompt from file: {prompt_file}")
                        return content
            except Exception as e:
                print(f"Error reading prompt file {prompt_file}: {e}")
        else:
            print(f"Warning: Prompt file {prompt_file} not found.")

    prompt_text = os.getenv("SUNA_TEST_PROMPT")
    if prompt_text:
        print("Using prompt from SUNA_TEST_PROMPT environment variable.")
        return prompt_text
        
    print("Using default fallback prompt.")
    return "Hello, this is a stress test message. Please ignore."

# Initialize prompt once at startup
TEST_PROMPT = get_test_prompt()
print(f"Test Prompt Preview: {TEST_PROMPT[:100]}...")

class SunaUser(HttpUser):
    wait_time = between(2, 5)
    thread_id = None
    
    def on_start(self):
        """
        Executed when a simulated user starts.
        We create a thread here so we can reuse it for chat messages.
        """
        self.client.headers.update({
            "Authorization": f"Bearer {JWT_TOKEN}"
        })
        
        # 1. Create a Thread
        # We assume the user exists and the token is valid.
        # Based on backend/core/threads.py: create_thread
        response = self.client.post("/api/threads", data={"name": "Stress Test Thread"})
        
        if response.status_code == 200:
            data = response.json()
            self.thread_id = data.get("thread_id")
            print(f"User started. Created thread: {self.thread_id}")
        else:
            print(f"Failed to create thread: {response.text}")
            self.stop() # Stop this user if initialization fails

    @task
    def chat_message(self):
        """
        Simulate sending a message to the agent.
        """
        if not self.thread_id:
            return

        # Based on backend/core/agent_runs.py: unified_agent_start
        # Payload is multipart/form-data
        payload = {
            "thread_id": self.thread_id,
            "prompt": TEST_PROMPT,
            "model_name": "openai/gpt-4o-mini" # Use a cheap/fast model or a mocked one if available
        }
        
        # Note: In Locust, passing 'data' makes it form-encoded or multipart depending on usage.
        # For multipart without files, we can just use 'data'.
        
        with self.client.post(
            "/api/agent/start", 
            data=payload, 
            name="/api/agent/start (Chat)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}: {response.text}")

    def on_stop(self):
        """
        Cleanup if necessary.
        """
        pass
