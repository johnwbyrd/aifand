"""Tests for the three-method pattern implementation."""

from aifand import Controller, Environment, Process, State, States


class TestThreeMethodPattern:
    """Test the three-method pattern in Process base class."""

    def test_default_three_method_pattern(self) -> None:
        """Test default three-method pattern execution."""

        class TestProcess(Process):
            def __init__(self, name: str) -> None:
                super().__init__(name=name)
                self.import_called = False
                self.think_called = False
                self.export_called = False
                self._test_states: States | None = None

            def _import_state(self, states: States) -> None:
                self.import_called = True
                self._test_states = states
                super()._import_state(states)

            def _think(self) -> None:
                self.think_called = True
                super()._think()

            def _export_state(self) -> States:
                self.export_called = True
                return self._test_states or States()

        process = TestProcess("test")
        input_states = States({"actual": State()})

        result = process.execute(input_states)

        # All three methods should have been called
        assert process.import_called
        assert process.think_called
        assert process.export_called

        # Result should be passed through unchanged by default
        assert result == input_states

    def test_stateless_controller_pattern(self) -> None:
        """Test stateless controller only overrides _think()."""

        class StatelessController(Controller):
            def __init__(self, name: str) -> None:
                super().__init__(name=name)
                self.executed = False
                self._controller_states: States | None = None

            def _import_state(self, states: States) -> None:
                self._controller_states = states

            def _think(self) -> None:
                # Simple pass-through but mark that we executed
                self.executed = True

            def _export_state(self) -> States:
                return self._controller_states or States()

        controller = StatelessController(name="stateless")

        input_states = States({"actual": State()})
        result = controller.execute(input_states)

        assert controller.executed
        assert result == input_states

    def test_ai_controller_pattern(self) -> None:
        """Test AI controller using all three methods."""

        class AIController(Controller):
            def __init__(self, name: str) -> None:
                super().__init__(name=name)
                self.internal_data = None
                self._ai_result = None

            def _import_state(self, states: States) -> None:
                # Simulate converting States to internal format
                self.internal_data = f"tensor_from_{len(states)}_states"

            def _think(self) -> None:
                # Simulate AI computation
                self._ai_result = f"ai_result_from_{self.internal_data}"

            def _export_state(self) -> States:
                # Convert AI result back to States
                # For test, just return states with a marker
                return States({"result": State(), "ai_processed": State()})

        ai_controller = AIController(name="ai")
        input_states = States({"actual": State(), "desired": State()})

        result = ai_controller.execute(input_states)

        assert ai_controller.internal_data == "tensor_from_2_states"
        assert "result" in result
        assert "ai_processed" in result

    def test_backward_compatibility_custom_execute(self) -> None:
        """Test backward compatibility for custom _execute()."""

        class CustomExecuteProcess(Process):
            def _execute(self, states: States) -> States:  # noqa: ARG002
                # Custom implementation bypasses three-method pattern
                self.custom_executed = True
                return States({"custom": State()})

        process = CustomExecuteProcess(name="custom")
        process.custom_executed = False

        input_states = States({"actual": State()})
        result = process.execute(input_states)

        assert process.custom_executed
        assert "custom" in result
        assert "actual" not in result  # Custom implementation replaced input

    def test_environment_inherits_pattern(self) -> None:
        """Test Environment inherits three-method pattern correctly."""

        class TestEnvironment(Environment):
            def __init__(self, name: str) -> None:
                super().__init__(name=name)
                self.env_executed = False
                self._env_states: States | None = None

            def _import_state(self, states: States) -> None:
                self._env_states = states

            def _think(self) -> None:
                # Environment logic
                self.env_executed = True

            def _export_state(self) -> States:
                return self._env_states or States()

        env = TestEnvironment(name="test_env")

        result = env.execute(States({"actual": State()}))

        assert env.env_executed
        assert result == States({"actual": State()})
