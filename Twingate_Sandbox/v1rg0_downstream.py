# v1rg0_downstream.py

class DownstreamActivator:
    def __init__(self, mock_api_callback, proposal_builder, bus_adapter=None):
        self._mock_api_callback = mock_api_callback
        self._proposal_builder = proposal_builder
        self._bus_adapter = bus_adapter
        self._activation_log = []

    def activate(self, proposal: dict) -> dict:
        # mock path only here
        result = self._mock_api_callback(proposal)
        entry = {
            "proposal_version": proposal.get("proposal_version"),
            "status": result.get("acknowledged"),
            "timestamp": time.time()
        }
        self._activation_log.append(entry)
        return {"status": "ACK", "timestamp": entry["timestamp"]}

    def on_proposal_received(self, proposal: dict) -> None:
        activation_result = self.activate(proposal)
        proposal["activation_result"] = activation_result

        if self._bus_adapter:
            self._bus_adapter.emit(
                event_type=V1rG0BusAdapter.EVENT_DOWNSTREAM_ACK,
                payload={
                    "proposal_version": proposal.get("proposal_version"),
                    "status": activation_result.get("status"),
                    "timestamp": activation_result.get("timestamp")
                },
                source="V1rG0.Downstream"
            )

    def pull_activation_log(self, limit: int = 10) -> list:
        return list(self._activation_log[-limit:])
