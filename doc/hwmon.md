# Linux Kernel hwmon sysfs Naming Conventions Analysis

The Linux kernel's hardware monitoring (hwmon) subsystem provides a standardized interface for hardware sensors through sysfs, but implementation analysis reveals both consistent patterns and significant violations that impact algorithmic sensor identification. This comprehensive analysis examines naming conventions across temperature, fan, PWM, voltage sensors, and alarm attributes to identify patterns suitable for automated sensor purpose detection.

## Core hwmon naming standard establishes clear patterns

The official hwmon interface follows a strict naming convention: `<type><number>_<item>` where type indicates sensor category, number provides unique identification, and item specifies the attribute. Temperature sensors use "temp", voltages use "in", fans use "fan", and PWM controls use "pwm". A critical inconsistency exists in numbering: **voltages start from 0** (in0, in1) due to datasheet conventions, while **all other sensors start from 1** (temp1, fan1, pwm1).

Standard attributes follow consistent suffixes across all sensor types. The `_input` suffix indicates current measured values, `_max` and `_min` define thresholds, `_crit` marks critical limits, and `_alarm` flags threshold violations. Labels use the `_label` suffix to provide human-readable descriptions. All values use fixed units: temperatures in millidegrees Celsius, voltages in millivolts, fan speeds in RPM, and PWM values from 0-255.

## Temperature sensor naming reveals driver-specific patterns

Temperature sensor implementations show remarkable consistency in basic naming but diverge significantly in semantic meaning. Intel's coretemp driver uses sequential numbering (temp1_input, temp2_input) for CPU cores with labels like "Core 0", "Core 1", and "Package id 0". Each sensor represents junction temperature with identical `temp*_max` values equaling TjMax.

AMD's k10temp driver demonstrates a fundamentally different approach. Pre-Zen CPUs report only Tctl (control temperature) as temp1_input - a non-physical value offset from actual temperature. Zen architecture adds Tdie (die temperature) as temp2_input and CCD temperatures as temp3_input through temp10_input. **This violates the assumption that temp1 represents actual temperature**, creating algorithmic challenges.

GPU drivers add another layer of complexity. AMD's amdgpu driver uses temp1_input for edge temperature, temp2_input for junction temperature, and temp3_input for memory temperature, with corresponding labels "edge", "junction", and "mem". NVIDIA's nouveau driver typically provides only temp1_input representing GPU core temperature. **The meaning of temp1 varies completely between CPU and GPU contexts**.

## Fan and PWM control patterns show implicit relationships

Fan monitoring follows consistent patterns with fan[1-*]_input reporting RPM values and fan[1-*]_min defining minimum speed thresholds. PWM control uses pwm[1-*] with values 0-255, where 255 equals 100% duty cycle. The critical pattern is **implicit numbering correlation**: pwm1 typically controls fan1, pwm2 controls fan2, establishing a 1:1 mapping.

Control modes use pwm[1-*]_enable with semi-standardized values. Mode 0 disables control (but behavior varies - some drivers run fans at full speed, others stop them completely). Mode 1 enables manual control via pwm[1-*] values. Mode 2 activates automatic control, but **modes 3+ are completely driver-specific**. The nct6775 driver uses modes 2-5 for "Thermal Cruise", "Fan Speed Cruise", "Smart Fan III", and "Smart Fan IV" respectively.

Temperature-to-fan relationships employ two mechanisms. Simple drivers use pwm[1-*]_temp_sel to specify a single temperature sensor index. Complex drivers implement pwm[1-*]_auto_channels_temp as a bitfield indicating multiple temperature inputs, with the highest temperature winning. Automatic control curves use pwm[1-*]_auto_point[1-*]_temp and pwm[1-*]_auto_point[1-*]_pwm to define temperature-to-PWM mappings.

## Voltage and alarm naming maintains consistency with notable exceptions

Voltage sensors follow the standard pattern but with the critical zero-based numbering exception. Common mappings include in0 for CPU core voltage (Vcore), in1 for +12V, in2 for +5V, and in3 for +3.3V, though **these mappings are conventions, not requirements**. Labels provide the only reliable identification method.

Alarm attributes demonstrate excellent consistency across all sensor types. Each sensor has a corresponding `*_alarm` attribute (in3_alarm, temp2_alarm, fan1_alarm) that indicates any threshold violation. Specific threshold alarms use `*_min_alarm`, `*_max_alarm`, `*_crit_alarm`, and `*_lcrit_alarm` suffixes. The `*_fault` suffix indicates hardware failures rather than threshold violations.

Power monitoring drivers like INA2xx add complexity by mixing voltage and current measurements. These drivers report bus voltage as in[1-3]_input but shunt voltage as in[4-6]_input, breaking the typical voltage rail association. PMBus drivers maintain better consistency by using descriptive labels like "vin", "vout1", "vout2" for their voltage channels.

## sysfs structure provides critical contextual disambiguation

The sysfs device path often provides the only reliable method to determine sensor purpose. Platform drivers appear under `/sys/devices/platform/` with descriptive names: `coretemp.0` for Intel CPUs, `k10temp.pci-00000000:00:18.3` for AMD CPUs, or `nct6775.656` for Super I/O chips. **The path prefix immediately identifies the sensor domain**.

GPU sensors reside under PCIe paths like `/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0/hwmon/` with additional context from `/sys/class/drm/card0/device/hwmon/`. The DRM card association definitively identifies GPU-related sensors. I2C sensors appear under `/sys/devices/platform/i2c-*/` or `/sys/bus/i2c/devices/`, clearly indicating external sensor chips.

A critical issue emerges with hwmon numbering instability. The `/sys/class/hwmon/hwmon*` numbers change between boots based on driver load order. **Stable sensor identification requires using device-specific paths** like `/sys/devices/platform/coretemp.0/hwmon/*/temp1_input` rather than `/sys/class/hwmon/hwmon2/temp1_input`.

## Documented violations complicate algorithmic detection

Several systematic violations challenge automated sensor identification. The **PWM scaling inconsistency** represents a major issue - while the standard mandates 0-255 scaling, some embedded systems use 0-100 percentage-based control. Scripts assuming standard scaling can set fans to 39% speed (100/255) when intending 100%.

The **semantic overloading of temp1** creates severe ambiguity. On Intel CPUs it means package temperature, on AMD CPUs it's control temperature (not physical), on AMD GPUs it's edge temperature, and on motherboard chips it typically indicates CPU socket temperature. Without examining device paths and labels, algorithmic differentiation becomes impossible.

**Missing or inconsistent labels** compound identification challenges. While coretemp provides descriptive labels like "Core 0", many drivers omit labels entirely. Even when present, label formats vary wildly - "CPU Temperature" vs "CPU" vs "Processor" for identical sensors. The ACPI thermal zone creates hwmon interfaces with generic names like "acpitz" that provide no semantic information.

## Thermal zone relationships add complexity

The Linux thermal framework creates parallel sensor hierarchies. ACPI thermal zones under `/sys/class/thermal/thermal_zone*/` spawn corresponding hwmon interfaces, but **the same physical sensor appears with different names and paths**. A CPU temperature might appear as thermal_zone0 (type="x86_pkg_temp") and simultaneously as a coretemp hwmon sensor.

The thermal-to-hwmon mapping uses the hwmon[1-*] subdirectory within thermal zones, but this represents yet another unstable numbering scheme. Correlation requires matching thermal zone types to hwmon device names, adding another layer of complexity to sensor identification algorithms.

## Algorithmic sensor identification strategies emerge from patterns

Successful sensor identification requires a multi-stage approach. First, **enumerate all hwmon devices** through `/sys/class/hwmon/hwmon*/` and immediately resolve their stable device paths through the device symlink. Next, **read the name attribute** to identify the driver type, providing initial context about expected sensors.

For each sensor, **check for label attributes first** as they provide the most reliable identification when present. Parse the label for keywords indicating sensor purpose: "Core" for CPU cores, "Package" for CPU package, "edge"/"junction" for GPU temperatures, "VCore"/"+12V"/"+5V" for voltage rails.

**Analyze the device path** to determine sensor domain. Platform paths indicate CPU or motherboard sensors, PCIe paths indicate GPUs, I2C paths indicate external monitoring chips. The path structure often disambiguates otherwise identical sensor names.

For fan control relationships, **correlate PWM and fan numbers** using the implicit mapping (pwm1→fan1). Read pwm[1-*]_temp_sel or pwm[1-*]_auto_channels_temp to identify temperature sources. Test PWM scaling by reading current values and checking against fan speeds to detect 0-255 vs 0-100 implementations.

## Conclusion

The Linux hwmon subsystem demonstrates both the benefits and challenges of standardization efforts. While core naming conventions provide a solid foundation, driver-specific implementations, historical decisions, and hardware variations create significant inconsistencies. Successful algorithmic sensor identification requires combining multiple information sources: sysfs paths for context, labels for semantic information, and careful validation of assumptions about numbering and scaling. The patterns identified here enable robust sensor detection, but algorithms must remain defensive against violations and prepared to handle missing information gracefully.