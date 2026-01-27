import os
import random
import time
from locust import HttpUser, task, between, events
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv("SUNA_API_KEY")

if not API_KEY:
    print("WARNING: SUNA_API_KEY env var not set. Requests will likely fail.")

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
        if API_KEY:
             self.client.headers.update({
                "x-api-key": API_KEY
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
        Simulate sending a message to the agent and waiting for completion.
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
        
        # Record start time for the entire flow
        start_time = time.time()
        agent_run_id = None
        
        # 1. Trigger Agent Run
        with self.client.post(
            "/api/agent/start", 
            data=payload, 
            name="/api/agent/start (Trigger)",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    agent_run_id = data.get("agent_run_id")
                    response.success()
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Status {response.status_code}: {response.text}")
                return # Stop if trigger failed

        if not agent_run_id:
            return

        # 2. Poll for Completion
        # We loop until the status is terminal (completed, failed, stopped, error)
        while True:
            # Sleep to avoid flooding the server with poll requests
            time.sleep(10) 
            
            with self.client.get(
                f"/api/agent-run/{agent_run_id}",
                name="/api/agent-run/{id} (Poll)",
                catch_response=True
            ) as poll_resp:
                if poll_resp.status_code != 200:
                    poll_resp.failure(f"Polling failed: {poll_resp.status_code}")
                    # Record failure for the whole flow
                    events.request.fire(
                        request_type="Flow",
                        name="Complete Agent Run",
                        response_time=(time.time() - start_time) * 1000,
                        response_length=0,
                        exception=Exception(f"Polling failed: {poll_resp.status_code}")
                    )
                    break
                
                try:
                    run_data = poll_resp.json()
                    status = run_data.get("status")
                    
                    if status in ["completed", "failed", "stopped", "error"]:
                        total_time = (time.time() - start_time) * 1000
                        
                        # Determine if the flow was successful
                        exception = None
                        if status != "completed":
                            exception = Exception(f"Agent run ended with status: {status}")
                        
                        # Fire a custom event to track the full duration
                        events.request.fire(
                            request_type="Flow",
                            name="Complete Agent Run",
                            response_time=total_time,
                            response_length=0,
                            exception=exception
                        )
                        break
                    # If still running, continue loop
                except Exception as e:
                    poll_resp.failure(f"JSON parse error: {e}")
                    break

    def on_stop(self):
        """
        Cleanup if necessary.
        """
        pass
