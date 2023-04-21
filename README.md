noizu-ops
============================
Simple interactive chat-gpt console session
with markdown formatted output and ability to commands as needed. 

# Usage

## Single Line Query
```
$ noizu-ops "Simple Query
> "Answer to query"
```


## Interactive Session
```
$ noizu-ops --session "configure routing table"
> Hello I am help you with: "confugure routing table"
> Please describe your task?
? ...
> This will require many steps would you like me to spawn a screen session?
(y/N) ?
> Okay 
[ Response ]
? ! ls -lh
```


# Intallation
You may install the latest version via pip. 

```bash
pip install noizu-ops 

# make user ~/.local/bin in in your path if not add this to your ~/.bashrc  or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

```

# Config

On your first run the system will ask your for your name, email address and open ai key. 
No data is currently shared with our servers.

We will eventually add support for uploading sessions/articles to review/share on the cload as well as support for uploading custom docs for custom tools/server configs so that GPT may scan to answer queries about unique server setup for team members.


