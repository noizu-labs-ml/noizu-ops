import textwrap
from enum import Enum
from typing import Optional

from lxml import etree

class ThoughtType(Enum):
    OTHER = 0
    THOUGHT = 1
    QUESTION = 2
    ASSUMPTION = 3
    INNER_CRITIC = 4
    TANGENT = 5

class TagBase(etree.ElementBase):
    def extract_child(self, tag: str):
        child = self.cssselect(tag)
        if len(child) > 0:
            child = child[0]
            return child.text.strip()
        return None

class SetConditionTag(TagBase):
    @property
    def name(self):
        return self.get("name")

    @property
    def prompt(self):
        prompt = self.extract_child("prompt")
        if prompt:
            return prompt
        else:
            name = self.get("name")
            return f"Set {name}"

    @property
    def choices(self):
        choices = []
        x = self.cssselect("choices choice")
        if len(x) > 0:
            for c in x:
                c_value = c.get("value")
                c_label = c.text or c_value
                i = None
                c_user = c.get("data-user") == "true"
                if c_user:
                    i = {
                        'prompt': c.get("data-prompt") or f"Enter {c_label}",
                        'required': c.get("data-required") == "true",
                        'check': c.get("data-check")
                    }
                choices.append({
                    'value': c_value,
                    'label': c_label,
                    'prompt': i
                })
        return choices








class ThoughtTag(TagBase):
    THOUGHT_TYPES = {
        "tangent": ThoughtType.TANGENT,
        "thought": ThoughtType.THOUGHT,
        "question": ThoughtType.QUESTION,
        "assumption": ThoughtType.ASSUMPTION,
        "inner-critic": ThoughtType.INNER_CRITIC
    }


    def _init(self):
        self.tag = "cot"

    @property
    def type(self):
        return self.THOUGHT_TYPES.get(self.get("type"), ThoughtType.OTHER)

    @property
    def thought(self):
        return self.text

    @property
    def markdown(self):
        type = self.THOUGHT_TYPES.get(self.get("type"), ThoughtType.OTHER)
        if type == ThoughtType.THOUGHT:
            type = "Thought"
        elif type == ThoughtType.QUESTION:
            type = "Question"
        elif type == ThoughtType.ASSUMPTION:
            type = "Assumption"
        elif type == ThoughtType.INNER_CRITIC:
            type = "Inner-Critic"
        elif type == ThoughtType.TANGENT:
            type = "Tangent"
        else:
            type = "Other"
        body = self.text.replace("`","'")
        return f"`{type}: {body}`"

class ExecTag(TagBase):
    def _init(self):
        self.tag = "exec"

    @property
    def shell(self):
        return self.get("shell")

    @property
    def exec_if(self):
        return self.get("exec-if", "true")

    @property
    def title(self):
        return self.extract_child("title") or "Run Command"

    @property
    def purpose(self):
        return self.extract_child("purpose") or "No Purpose Provided"

    @property
    def command(self):
        return self.extract_child("command")

    @property
    def markdown(self):
        title = self.extract_child("title") or "Run Command"
        title = textwrap.indent(title, "# ")
        shell = self.get("shell")
        command = self.extract_child("command") or ""

        template = textwrap.dedent(
            """
            ```{shell}
            {title}
            
            {command}
            ```
            """
        ).strip().format(
            title=title,
            shell=shell,
            command=command
        )
        return template


class SmahLookup(etree.CustomElementClassLookup):
    def lookup(self, node_type, document, namespace, name):
        if node_type == "element":
            if name == "exec":
                return ExecTag
            elif name == "cot":
                return ThoughtTag
            elif name == "set-condition":
                return SetConditionTag
        return None

class ResponseParser:
    def __init__(self):
        pass

    @staticmethod
    def replace_tag(elem: any, replace: str):
        ps = elem.getprevious()
        p = elem.getparent()
        if ps is not None:
            ps.tail += replace
        elif p is not None:
            p.text += replace
        if p is not None:
            p.remove(elem)


    @staticmethod
    def extract_conditions(response: str, options: Optional[dict] = None) -> Optional[list]:
        options = options or {}
        parser = etree.XMLPullParser(recover=True)
        parser.set_element_class_lookup(SmahLookup())
        events = parser.read_events()

        parser.feed("<smah-msg>" + response + "</smah-msg>")
        response = []
        for action, elem in events:
            if action == "end":
                if isinstance(elem, SetConditionTag):
                    c = {
                        'name': elem.name,
                        'prompt': elem.prompt,
                        'choices': elem.choices
                    }
                    response.append(c)
        return response

    @staticmethod
    def extract_commands(response: str, options: Optional[dict] = None) -> Optional[list]:
        options = options or {}
        parser = etree.XMLPullParser()
        parser.set_element_class_lookup(SmahLookup())
        events = parser.read_events()

        parser.feed("<smah-msg>" + response + "</smah-msg>")
        commands = []
        for action, elem in events:
            if action == "end":
                if isinstance(elem, ExecTag):
                    conditions = options.get("conditions") or {}
                    # include operator and system
                    c = elem.exec_if
                    c = c.format(**conditions)
                    if eval(c, conditions):
                        c = {
                            'title': elem.title,
                            'purpose': elem.purpose,
                            'command': elem.command,
                            'shell': elem.shell
                        }
                        commands.append(c)
                    else:
                        print(f"Skipping command: {elem.title} due to falsy condition: {c}")
        return commands

    @staticmethod
    def to_markdown(response: str, options: Optional[dict] = None) -> str:
        options = options or {}
        parser = etree.XMLPullParser()
        parser.set_element_class_lookup(SmahLookup())
        events = parser.read_events()

        parser.feed("<smah-msg>" + response + "</smah-msg>")
        for action, elem in events:
            if action == "end":
                if isinstance(elem, ExecTag):
                    ResponseParser.replace_tag(elem, elem.markdown + (elem.tail or ""))
                elif isinstance(elem, SetConditionTag):
                    ResponseParser.replace_tag(elem, elem.tail or "")
                elif isinstance(elem, ThoughtTag):
                    ResponseParser.replace_tag(elem, (elem.tail or "") if options.get('strip-cot', True) else elem.markdown + (elem.tail or ""))

        root = parser.close()
        response = etree.tostring(root, pretty_print=True).decode()
        return response[len("<smah-msg>"):-(len("</smah-msg>") + 1)]



