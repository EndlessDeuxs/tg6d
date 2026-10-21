# orchestrator_core.py - main loop
import os
import time
from v1rgo_keychain import V1rgoKeychain
from v1rgo_prompt_injector import V1rgoPromptInjector
from v1rgo_transmission_suit import V1rgoTransmissionSuit
from v1rgo_validation_gate import V1rgoValidationGate

class MemoryStore:
    def log_event(self, event_type: str, data: dict):
        print(f"[MEMORY] {event_type}: {json.dumps(data, default=str)[:200]}")

class ProposalBuilder:
    def push_event(self, event: dict):
        print(f"[PROPOSAL] Event received: {event.get('type')}")

class DLQHandler:
    def push(self, result: dict, task: dict):
        print(f"[DLQ] Error queued for task {task.get('task_id')}: {result.get('error')}")

if __name__ == "__main__":
    keychain = V1rgoKeychain(master_password=os.environ.get("V1RGO_MASTER_PW", "default_dev_password"))
    injector = V1rgoPromptInjector()
    transmission_suit = V1rgoTransmissionSuit(keychain)
    validation_gate = V1rgoValidationGate()
    memory_store = MemoryStore()
    proposal_builder = ProposalBuilder()
    dlq_handler = DLQHandler()

    while True:
        task = injector.get_task()
        if not task:
            time.sleep(1)
            continue

        task_validation = validation_gate.validate_task(task)
        if not task_validation["valid"]:
            memory_store.log_event("task_validation_failed", {"task_id": task.get("task_id", "unknown"), "errors": task_validation["errors"]})
            continue

        model_id = task["payload"].get("model_id", "claude_sonnet_5")
        result = transmission_suit.transmit(model_id, task["payload"])

        result_validation = validation_gate.validate_result(result)
        if not result_validation["valid"]:
            memory_store.log_event("result_validation_failed", {"task_id": task["task_id"], "errors": result_validation["errors"]})
            dlq_handler.push(result, task)
            continue

        content = validation_gate.extract_content(result, model_id)
        if content:
            memory_store.log_event("content_received", {"task_id": task["task_id"], "model_id": model_id, "content_preview": content[:200]})
            proposal_builder.push_event({"type": "model_response", "task_id": task["task_id"], "content": content})

        memory_store.log_event("transmission_complete", {"task_id": task["task_id"], "model_id": model_id, "result_status": result["status"]})