"""Fixed-value controller for constant thermal output."""

from pydantic import Field

from aifand import Actuator, Controller, State, States


class FixedSpeedController(Controller):
    """Controller that applies fixed values to actuators.

    FixedSpeedController is a simple stateless controller that applies
    configured fixed values to actuators. This controller requires no
    memory or historical data.

    The controller applies fixed actuator settings from configuration,
    making it useful for testing, debugging, and scenarios where
    constant thermal output is desired.
    """

    actuator_settings: dict[str, float] = Field(
        default_factory=dict,
        description="Dictionary mapping actuator names to fixed values",
    )

    def _execute(self, states: States) -> States:
        """Apply fixed actuator values to states.

        Args:
            states: Dictionary of named input states

        Returns:
            Dictionary containing desired state with actuator commands
        """
        # Start with a copy of input states
        result_states = States(states)

        # Apply fixed settings to actuators in desired state
        for actuator_name, fixed_value in self.actuator_settings.items():
            # Create actuator with fixed value
            actuator = Actuator(
                name=actuator_name,
                properties={"value": fixed_value},
            )

            # Add actuator to desired state (create if doesn't exist)
            if "desired" not in result_states:
                result_states["desired"] = State()

            result_states["desired"] = result_states["desired"].with_device(
                actuator
            )

        return result_states
