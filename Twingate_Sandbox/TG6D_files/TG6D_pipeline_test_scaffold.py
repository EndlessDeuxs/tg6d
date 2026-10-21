# Twingate Pipeline Test Scaffold - v0.2.0
# Status: BUILD_R execution at Depth 3/3
# Expected output: pytest-compatible test suite
#
# Chambers under test:
# - Controller-like orchestration (Pipeline)
# - Pulse routing & chamber heartbeat
# - Synthesis continuity across depths
# - DLQ integrity for malformed pulses
# - Autocraft vector (mechanical deployment placeholder)

import pytest
from unittest.mock import AsyncMock, patch

from twingate.pipeline import Pipeline, Pulse, PulseType
from twingate.autocraft import AutocraftEngine, AutocraftState  # conceptual future vector


class TestPipelineEndToEnd:
    """End-to-end pipeline integrity verification (Depth 2 → 3 → Autocraft-ready)."""

    @pytest.fixture
    async def pipeline(self):
        p = Pipeline()
        await p.initialize()
        yield p
        await p.shutdown()

    @pytest.fixture
    async def autocraft(self):
        """
        Autocraft system fixture.
        Conceptual mechanical deployment engine; validates that
        pipeline signals are consumable by downstream automation.
        """
        engine = AutocraftEngine()
        await engine.initialize()
        yield engine
        await engine.shutdown()

    @pytest.mark.asyncio
    async def test_heartbeat_propagation(self, pipeline):
        """Verify HEARTBEAT pulses traverse all chambers with ACKs."""
        test_pulse = Pulse(type=PulseType.HEARTBEAT, source="ANALYTICS")
        result = await pipeline.process(test_pulse)

        assert result.status == "delivered"
        assert all(chamber.heartbeat_ack for chamber in pipeline.chambers)

    @pytest.mark.asyncio
    async def test_synthesis_continuity_depth_transition(self, pipeline):
        """Verify SYNTHESIS output preserves depth context (2 → 3)."""
        depth_2_state = {"wcr_depth": 2, "collectick": 8, "tick": 6}
        result = await pipeline.synthesize(depth_2_state)

        assert result.depth == 3
        assert result.continuity_flag is True
        assert result.metadata["source_depth"] == 2

    @pytest.mark.asyncio
    async def test_dlq_recovery_for_malformed_pulses(self, pipeline):
        """Verify dead letter queue handles malformed pulses cleanly."""
        bad_pulse = Pulse(type="INVALID", payload=None)

        with patch.object(pipeline.api_handler, "handle") as mock_handle:
            mock_handle.side_effect = ValueError("Bad data")
            result = await pipeline.process(bad_pulse)

        assert result.dlq_count == 1
        assert pipeline.api_handler.dlq_size() == 1
        assert pipeline.api_handler.last_error == "Bad data"

    @pytest.mark.asyncio
    async def test_autocraft_signal_compatibility(self, pipeline, autocraft):
        """
        Verify Autocraft system can consume pipeline synthesis output
        as a mechanical deployment signal without loss of depth context.
        """
        depth_state = {"wcr_depth": 3, "collectick": 8, "tick": 6}
        synth = await pipeline.synthesize(depth_state)

        # Autocraft interprets synthesis output as a deployment plan
        autocraft_state: AutocraftState = await autocraft.ingest_signal(synth)

        assert autocraft_state.ready is True
        assert autocraft_state.source_depth == 3
        assert autocraft_state.deployment_vector == "mechanical"
        assert autocraft_state.validation_passed is True

    @pytest.mark.asyncio
    async def test_autocraft_feedback_loop(self, pipeline, autocraft):
        """
        Ensure Autocraft can emit feedback pulses back into the pipeline,
        closing the loop for future mechanical deployments.
        """
        # Autocraft emits a PULSE back to the pipeline
        feedback_pulse = await autocraft.emit_feedback_pulse(
            source="AUTOCRAFT",
            kind=PulseType.HEARTBEAT,
            payload={"mechanical_ready": True},
        )

        result = await pipeline.process(feedback_pulse)

        assert result.status == "delivered"
        assert any(
            getattr(chamber, "autocraft_ack", False)
            for chamber in pipeline.chambers
        )
