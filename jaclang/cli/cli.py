"""This is the implementation of the command line interface tool for the Jac language.

It's built with the Jac language via bootstraping and
represents the first such complete Jac program.
"""
from __future__ import annotations

import argparse
import cmd
import inspect
import typing as _jac_typ

from jaclang.jac.plugin.feature import JacFeature as _JacFeature


@_JacFeature.make_architype("obj", on_entry=[], on_exit=[])
class Command:
    """
    Represents a command in the command line interface.

    Attributes:
    - func: The callable function associated with the command.
    - sig: The signature of the function.
    """

    func: callable
    sig: inspect.Signature

    def __init__(self, func: callable) -> None:
        """
        Initialize a Command instance.

        Parameters:
        - func: The callable function associated with the command.
        """
        self.func = func
        self.sig = inspect.signature(func)

    def call(self, *args: list, **kwargs: dict) -> None:
        """
        Call the associated function with the specified arguments and keyword arguments.

        Parameters:
        - *args: Positional arguments.
        - **kwargs: Keyword arguments.
        """
        return self.func(*args, **kwargs)


@_JacFeature.make_architype("obj", on_entry=[], on_exit=[])
class CommandRegistry:
    """
    Registry for managing commands in the command line interface.

    Attributes:
    - registry: A dictionary mapping command names to Command instances.
    - sub_parsers: Argument parser sub-parsers for individual commands.
    - parser: Main argument parser for the CLI.

    Methods:
    - register(func: callable) -> None: Register a command in the registry.
    - get(name: str) -> Command: Get the Command instance for a given command name.
    - items() -> dict[str, Command]: Get all registered commands as a dictionary.
    """

    registry: dict[str, Command]
    sub_parsers: argparse._SubParsersActionp
    parser: argparse.ArgumentParser

    def __init__(self) -> None:
        """Initialize a CommandRegistry instance."""
        self.registry = {}
        self.parser = argparse.ArgumentParser(prog="CLI")
        self.sub_parsers = self.parser.add_subparsers(title="commands", dest="command")

    def register(self, func: callable) -> None:
        """
        Register a command in the registry.

        Parameters:
        - func: The callable function representing the command.

        Returns:
        - None
        """
        name = func.__name__
        cmd = Command(func)
        self.registry[name] = cmd
        cmd_parser = self.sub_parsers.add_parser(name)
        # param_items = cmd.sig.parameters.items
        first = True
        for param_name, param in cmd.sig.parameters.items():
            if param_name == "args":
                cmd_parser.add_argument("args", nargs=argparse.REMAINDER)
            elif param.default is param.empty:
                if first:
                    first = False
                    cmd_parser.add_argument(
                        f"{param_name}", type=eval(param.annotation)
                    )
                else:
                    cmd_parser.add_argument(
                        f"-{param_name[:1]}",
                        f"--{param_name}",
                        required=True,
                        type=eval(param.annotation),
                    )
            elif first:
                first = False
                cmd_parser.add_argument(
                    f"{param_name}", default=param.default, type=eval(param.annotation)
                )
            else:
                cmd_parser.add_argument(
                    f"-{param_name[:1]}",
                    f"--{param_name}",
                    default=param.default,
                    type=eval(param.annotation),
                )
        return func

    def get(self, name: str) -> Command:
        """
        Get the Command instance for a given command name.

        Parameters:
        - name: The name of the command.

        Returns:
        - Command: The Command instance for the specified command name.
        """
        return self.registry.get(name)

    def items(self) -> dict[str, Command]:
        """
        Get all registered commands as a dictionary.

        Returns:
        - dict[str, Command]: A dictionary mapping command names to Command instances.
        """
        return self.registry.items()


@_JacFeature.make_architype("obj", on_entry=[], on_exit=[])
class CommandShell(cmd.Cmd):
    """
    Command shell for the command line interface.

    Attributes:
    - intro: Introduction message displayed at the start.
    - prompt: Prompt string.
    - cmd_reg: CommandRegistry instance.

    Methods:
    - do_exit(arg: list) -> bool: Exit the command shell.
    - default(line: str) -> None: Default method for processing commands.
    """

    intro: _jac_typ.ClassVar[str] = "Welcome to the Jac CLI!"
    prompt: _jac_typ.ClassVar[str] = "jac> "
    cmd_reg: CommandRegistry

    def __init__(self, cmd_reg: CommandRegistry) -> None:
        """
        Initialize a CommandShell instance.

        Parameters:
        - cmd_reg: CommandRegistry instance.
        """
        self.cmd_reg = cmd_reg
        super().__init__()

    def do_exit(self, arg: list) -> bool:
        """
        Exit the command shell.

        Parameters:
        - arg: Command arguments.

        Returns:
        - bool: True to exit the shell.
        """
        return True

    def default(self, line: str) -> None:
        """
        Process the command line input.

        Parameters:
        - line: The command line input.
        """
        try:
            args = vars(self.cmd_reg.parser.parse_args(line.split()))
            command = self.cmd_reg.get(args["command"])
            if command:
                args.pop("command")
                ret = command.call(**args)
                if ret:
                    print(ret)
        except Exception as e:
            print(e)


cmd_registry = CommandRegistry()


def start_cli() -> None:
    """
    Start the command line interface.

    Returns:
    - None
    """
    parser = cmd_registry.parser
    args = parser.parse_args()
    command = cmd_registry.get(args.command)
    if command:
        args = vars(args)
        args.pop("command")
        ret = command.call(**args)
        if ret:
            print(ret)
    else:
        shell = CommandShell(cmd_registry).cmdloop()
        shell.cmdloop()


if __name__ == "__main__":
    start_cli()
