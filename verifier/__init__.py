"""The deterministic verifier: each tool's checks, and the task's, on contract instances."""

from contract import Task, Tool

from . import fifths

# tool -> (verify_input(value), verify_output(input_value, output_value, workspace))
TOOLS = {
    Tool.GET_CHART: (fifths.seed_check, lambda given, made, workspace: fifths.verify_chart_output(given, made)),
    Tool.KEY_INFO: (fifths.key_check, lambda given, made, workspace: fifths.verify_key_output(given, made)),
    Tool.PIN_TRANSPOSITION: (fifths.seed_check, lambda given, made, workspace: fifths.verify_pin_output(given, made)),
}
# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.TRANSPOSE_CHART: fifths.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)][0](value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)][1](input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
