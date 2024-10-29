import textwrap
import difflib
from typing import Optional

from rich.markdown import Markdown

from smah.console import std_console
from smah.runner.response_parser import ResponseParser

def sut(scenario: str = "default", options: Optional[dict] = None):
    if scenario == "cot":
        return sut__cot(options)
    elif scenario == "mixed":
        return sut__mixed(options)
    return sut__default(options)

def sut__default(options: Optional[dict] = None):
    return sut__cot(options)


def sut__mixed(options: Optional[dict] = None):
    options = options or {}
    type = options.get("type", "thought")
    msg = options.get("msg", "I wonder if this is all there is")
    return textwrap.dedent(
        """
        # Before
        ...

        <cot type="{type}">{msg}</cot>
        
        <exec shell="zsh">
        <title>Echo Hello World</title>
        <purpose>Show how to echo Hello World to the console</purpose>
        <command>
        echo "Hello World"
        </command>
        </exec>

        # After
        ...
        """
    ).format(
        type=type,
        msg=msg
    )

def sut__cot(options: Optional[dict] = None):
    options = options or {}
    type = options.get("type", "thought")
    msg = options.get("msg", "I wonder if this is all there is")
    return textwrap.dedent(
        """
        # Before
        ...
        
        <cot type="{type}">{msg}</cot>
        
        # After
        ...
        """
    ).format(
        type=type,
        msg=msg
    )


def test_cot_to_md():
    message = sut("cot")
    md = ResponseParser.to_markdown(message)
    expected = textwrap.dedent(
        """
        # Before
        ...
        
        `Thought: I wonder if this is all there is`
        
        # After
        ...
        """
    )
    assert md == expected, f"Expected:\n{expected}\n---\nActual:\n{md}"


def test_cot_and_exec_to_md():
    message = sut("mixed")
    md = ResponseParser.to_markdown(message)
    expected = textwrap.dedent(
        """
        # Before
        ...

        `Thought: I wonder if this is all there is`
                
        ***Echo Hello World:***
        Show how to echo Hello World to the console
        
        ```zsh
        echo "Hello World"
        ```

        # After
        ...
        """
    )
    assert md == expected, f"\nExpected:\n{expected}\n---\nActual:\n{md}"