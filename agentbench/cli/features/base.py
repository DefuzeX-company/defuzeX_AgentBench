"""Composable command registration for the AgentBench CLI."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace, _SubParsersAction
from collections.abc import Callable
from dataclasses import dataclass


CommandHandler = Callable[[Namespace], int]
ParserConfigurator = Callable[[ArgumentParser], None]


@dataclass(frozen=True)
class CommandFeature:
    """One independently implemented AgentBench subcommand."""

    name: str
    help: str
    description: str
    configure: ParserConfigurator
    execute: CommandHandler
    default: bool = False

    def register(self, subparsers: _SubParsersAction[ArgumentParser]) -> None:
        parser = subparsers.add_parser(
            self.name,
            help=self.help,
            description=self.description,
        )
        self.configure(parser)
        parser.set_defaults(command_handler=self.execute)
