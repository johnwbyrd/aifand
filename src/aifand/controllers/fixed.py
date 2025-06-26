"""Fixed-value controller for constant thermal output."""

from pydantic import Field

from ..base.device import Actuator  # noqa: TID252
from ..base.process import Controller  # noqa: TID252
from ..base.state import State  # noqa: TID252


class FixedSpeedController(Controller):
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

    def _think(self, states: dict[str, State]) -> dict[str, State]:
        """Apply fixed actuator values to states.

        Demonstrates stateless pattern by overriding only _think().
        Creates or updates actuators with fixed values from
        configuration.

        Args:
            states: Input states dictionary

        Returns:
            States with actuators set to fixed values

        """
        result_states = dict(states)

        # Apply fixed settings to actuators
        for actuator_name, fixed_value in self.actuator_settings.items():
            # Create or update actuator with fixed value
            actuator = Actuator(
                name=actuator_name,
                properties={"value": fixed_value},
            )

            # Add actuator to actual state (create if doesn't exist)
            if "actual" not in result_states:
                result_states["actual"] = State()

            result_states["actual"] = result_states["actual"].with_device(
                actuator
            )

        return result_states
