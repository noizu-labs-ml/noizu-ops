import textwrap
from enum import Enum
from lxml import etree

class ThoughtType(Enum):
    OTHER = 0
    THOUGHT = 1
    QUESTION = 2
    ASSUMPTION = 3
    INNER_CRITIC = 4

class ThoughtTag(etree.ElementBase):
    THOUGHT_TYPES = {
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
        else:
            type = "Other"
        body = self.text.replace("`","\\`")
        return f"`{type}: {body}`"

class ExecTag(etree.ElementBase):
    def _init(self):
        self.tag = "exec"

    @property
    def shell(self):
        return self.get("shell")

    def extract_child(self, tag: str):
        child = self.cssselect(tag)
        if len(child) > 0:
            child = child[0]
            return child.text.strip()
        return None

    @property
    def markdown(self):
        title = self.extract_child("title") or "Run Command"
        purpose = self.extract_child("purpose") or "No Purpose Provided"
        shell = self.get("shell")
        command = self.extract_child("command") or ""

        template = textwrap.dedent(
            """
            ***{title}:***
            {purpose}
            
            ```{shell}
            {command}
            ```
            """
        ).strip().format(
            title=title,
            purpose=purpose,
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
        return None

class ResponseParser:
    def __init__(self):
        pass

    @staticmethod
    def to_markdown(response: str):
        parser = etree.XMLPullParser()
        parser.set_element_class_lookup(SmahLookup())
        events = parser.read_events()

        parser.feed("<smah-msg>" + response + "</smah-msg>")
        for action, elem in events:
            if action == "end":
                if isinstance(elem, ExecTag) or isinstance(elem, ThoughtTag):
                    ps = elem.getprevious()
                    p = elem.getparent()
                    md = elem.markdown + elem.tail
                    if ps is not None:
                        ps.tail += md
                    elif p is not None:
                        p.text += md

                    if p is not None:
                        p.remove(elem)
        root = parser.close()
        response = etree.tostring(root, pretty_print=True).decode()
        return response[len("<smah-msg>"):-(len("</smah-msg>") + 1)]



