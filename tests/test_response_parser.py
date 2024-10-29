import textwrap
import difflib
from typing import Optional

import rich
from rich.markdown import Markdown

from smah.console import std_console
from smah.runner.response_parser import ResponseParser

def sut(scenario: str = "default", options: Optional[dict] = None):
    if scenario == "cot":
        return sut__cot(options)
    elif scenario == "mixed":
        return sut__mixed(options)
    elif scenario == "indented":
        return sut__indented(options)
    return sut__default(options)

def sut__default(options: Optional[dict] = None):
    return sut__cot(options)


def sut__indented(options: Optional[dict] = None):
    options = options or {}
    type = options.get("type", "thinking")
    msg = options.get("msg", "I wonder if this is all there is")
    return textwrap.dedent(
        """\
        # Before
        ...
        - first
            <cot type="{type}">{msg}</cot>
        - second
            Command
            <exec shell="zsh" exec-if="apple==5">
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


def sut__mixed(options: Optional[dict] = None):
    options = options or {}
    type = options.get("type", "thinking")
    msg = options.get("msg", "I wonder if this is all there is")
    return textwrap.dedent(
        """\
        # Before
        ...

        <cot type="{type}">{msg}</cot>
        
        <exec shell="zsh" exec-if="apple==5">
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
    type = options.get("type", "thinking")
    msg = options.get("msg", "I wonder if this is all there is")
    return textwrap.dedent(
        """\
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
    md = ResponseParser.to_markdown(message, options={'strip-cot': False})
    expected = textwrap.dedent(
        """\
        # Before
        ...
        
        `Thinking: I wonder if this is all there is`
        
        # After
        ...
        """
    )
    assert md == expected, f"Expected:\n{expected}\n---\nActual:\n{md}"


def test_cot_and_exec_to_md():
    message = sut("mixed")
    md = ResponseParser.to_markdown(message, options={'strip-cot': False})
    expected = textwrap.dedent(
        """\
        # Before
        ...

        `Thinking: I wonder if this is all there is`
        
        ```zsh
        # Echo Hello World
        
        echo "Hello World"
        ```

        # After
        ...
        """
    )
    assert md == expected, f"\nExpected:\n{expected}\n---\nActual:\n{md}"


def test_indented_to_md():
    message = sut("indented")
    md = ResponseParser.to_markdown(message, options={'strip-cot': False})
    expected = textwrap.dedent(
        """\
        # Before
        ...
        - first
            `Thinking: I wonder if this is all there is`
        - second
            Command
            ```zsh
            # Echo Hello World
    
            echo "Hello World"
            ```

        # After
        ...
        """
    )
    assert md == expected, f"\nExpected:\n{expected}\n---\nActual:\n{md}"


def test_extract_commands():
    message = sut("mixed")
    commands = ResponseParser.extract_commands(message, {'conditions': {'apple': 4}})
    assert commands == []
    commands = ResponseParser.extract_commands(message, {'conditions': {'apple': 5}})
    assert len(commands) == 1

def test_escape_response():
    message = textwrap.dedent(
        """
        SECTION
        ===
        <div><b>Some text</b> Hey < There</div>
        """
    ).strip()
    escaped = ResponseParser.escape_response(message)
    assert escaped == "SECTION\n===\n<div><b>Some text</b> Hey :_smah_lt_: There</div>"
    m = ResponseParser.to_markdown(message)
    assert m == "SECTION\n===\n<div><b>Some text</b> Hey < There</div>"