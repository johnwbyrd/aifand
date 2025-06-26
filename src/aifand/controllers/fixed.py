"""Fixed-value controller for constant thermal output."""

from typing import Any

from pydantic import Field

from aifand import Actuator, Controller, State, StatefulProcess, States


class FixedSpeedController(Controller, StatefulProcess):
    """Controller that applies fixed values to actuators.

    FixedSpeedController demonstrates the simplest three-method pattern
    usage, overriding only _think() to apply configured fixed values to
    actuators. This controller is stateless and requires no memory or
    historical data.

    The controller applies fixed actuator settings from configuration,
    making it useful for testing, debugging, and scenarios where
    constant thermal output is desired.
    """

    actuator_settings: dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary mapping actuator names to fixed values",
    )

    def __init__(self, **data: Any) -> None:
        """Initialize FixedSpeedController with instance state vars."""
        super().__init__(**data)
        # Instance variables for three-method pattern communication
        self._actual_states: States | None = None
        self._desired_states: States | None = None

    def _import_state(self, states: States) -> None:
        """Store input states for _think() method access.

        Args:
            states: Dictionary of named input states
        """
        super()._import_state(states)  # Update Buffer (though unused)
        self._actual_states = States(states)
        self._desired_states = States(states)  # Start with input states

    def _think(self) -> None:
        """Apply fixed actuator values to states.

        Demonstrates stateless pattern by overriding only _think().
        Creates or updates actuators with fixed values from
        configuration and stores them in desired state.
        """
        if not self._actual_states or not self._desired_states:
            return

        # Apply fixed settings to actuators in desired state
        for actuator_name, fixed_value in self.actuator_settings.items():
            # Create actuator with fixed value
            actuator = Actuator(
                name=actuator_name,
                properties={"value": fixed_value},
            )

            # Add actuator to desired state (create if doesn't exist)
            if "desired" not in self._desired_states:
                self._desired_states["desired"] = State()

            self._desired_states["desired"] = self._desired_states[
                "desired"
            ].with_device(actuator)

    def _export_state(self) -> States:
        """Export the calculated states with desired actuator values.

        Returns:
            Dictionary containing desired state with actuator commands
        """
        return (
            States(self._desired_states) if self._desired_states else States()
        )
