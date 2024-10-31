SMAH
===

Welcome to **SMAH** the `S`yste`M` `A`dmin `H`elper that just so happens to be
`SM`art `A`s `H`ell), an early prototype of a suite of tools designed 
to assist system administrators, data scientists, developers,
and power users with system operations. 

SMAH helps simplify tasks by providing command generation, 
pipe processing and other tasks tailored to your background and operating system. 

## Purpose

SMAH is designed to:
1. **Generate Commands**: Avoid endless searches through documentation. Simply describe what you want to do, and SMAH generates the necessary command while explaining potential impacts and asking for confirmation before execution. You just want to use ffmpeg(tm) to convert a mp4 into a gif. 
2. **Assisted Pipe Generation**: Take advantage of SMAH’s ability to assist in generating complex pipes and chaining commands in Unix environments.
3. **AI-Assisted Monitoring (pending)**: Set up system monitoring tasks quickly with AI guidance, allowing you to keep track of critical metrics and thresholds without manual configuration.

## Key Features

- **Interactive Command Generation**: SMAH can guide you through setting up environments, managing packages, configuring system services, and more, by generating commands and helping you understand their implications before execution. And ask questions as it (pending) process your query.
- **User Preferences and Personalization**: SMAH remembers your preferences for certain tools (e.g., package managers, environment management tools) and uses those to generate optimal commands, saving time and reducing repetitive configuration.
- **Command Confirmation and Safety**: For safety and control, SMAH will always ask for confirmation before running any system-altering command. You’ll also be given an overview of what the command will do and the expected impact on your system.
- **Model Planning/Prompt Planning**: A fast model is used to look at a sample of pipe data or your inquiry in order to decide
the best output format, runner model, additional instructions nad other details.


# Installation


## Pip Install
```
pip install smah
# call smah to begin setup. 
smah --setup
```

or 

## Local Build
-  git checkout code
- install poetry and python env. 
- setup python env (conda, venv, etc.)
- navigate to smah folder and run `poetry install`
- set SMAH_OPENAI_API_KEY env variable or set key in your smah config file `~/.smah/config.yaml`
- run smah --setup

# Examples

##  Pipe Input Processing

### Log Audit to Pipe Output Format
Analyze Access Log Entries

```sh
tail -n 500 /var/log/auth.log | smah -q "Analyze these access log entries and output a tab-delimited list of top offending IPs, number of events, and a general statement why they are considered malicious/bad actors."
```
### System Task
```sh
smah -q "How do I setup a web proxy on this server that I can connect to via my remote desktop to access the web?"
 ```

### Resume last chat 

```sh
smah --continue
```

### Resume recent or (pending) search old conversations to pick up from.

```sh
smah --history
```

### Resume by id.

```sh
smah --session ID
```

### Interative Mode

```sh
smah --interactive
```

### Saved Prompt
```
systemctl status | smah -i ~/.scan-status.md 
```

### Help
```
> smah -h
usage: smah [-h] [-q QUERY] [-i INSTRUCTIONS] [--interactive | --no-interactive] [-c CONFIG] [--database DATABASE] [--configure | --no-configure] [--continue | --no-continue] [--session SESSION] [--history | --no-history]
            [-v] [--model MODEL] [--model-picker MODEL_PICKER] [--model-query MODEL_QUERY] [--model-pipe MODEL_PIPE] [--model-interactive MODEL_INTERACTIVE] [--model-review MODEL_REVIEW] [--model-edit MODEL_EDIT]
            [--openai-api-tier OPENAI_API_TIER] [--openai-api-key OPENAI_API_KEY] [--openai-api-org OPENAI_API_ORG] [--gui | --no-gui] [--rich | --no-rich]

SMAH Command Line Tool

options:
  -h, --help            show this help message and exit
  -q QUERY, --query QUERY
                        The Query to process
  -i INSTRUCTIONS, --instructions INSTRUCTIONS
                        The Instruction File to process
  --interactive, --no-interactive
                        Run in interactive mode (default: False)
  -c CONFIG, --config CONFIG
                        Path to alternative config file
  --database DATABASE   Path to sqlite smah database
  --configure, --no-configure
                        Enter Config Setup (default: False)
  --continue, --no-continue
                        Continue Last Conversation (default: False)
  --session SESSION     Resume Session
  --history, --no-history
                        Resume Recent Session (default: False)
  -v, --verbose         Set Verbosity Level, such as -vv
  --model MODEL         Default Model
  --model-picker MODEL_PICKER
                        Picker Model
  --model-query MODEL_QUERY
                        Query Model
  --model-pipe MODEL_PIPE
                        Pipe Processing Model
  --model-interactive MODEL_INTERACTIVE
                        Interactive Processing Model
  --model-review MODEL_REVIEW
                        Output Reviewer Model
  --model-edit MODEL_EDIT
                        Output Editor Model
  --openai-api-tier OPENAI_API_TIER
                        OpenAI Tier
  --openai-api-key OPENAI_API_KEY
                        OpenAI Api Key
  --openai-api-org OPENAI_API_ORG
                        OpenAI Api Org
  --gui, --no-gui       Run in GUI mode (default: False)
  --rich, --no-rich     Rich Format Output (default: True)
```



# Setup

```
pip install smah
```

## Getting Started
When you run `smah` for the first time, it will guide you through a setup process to configure the necessary settings. Here is a step-by-step walkthrough of what the first run setup flow looks like:

### 1. First Run
```sh
smah
```


# First Run Setup Flow

On the first run you will be asked about your background, experience,
and system details will be extracted or manually provided to reference 
future requests. 

system details will be extracted or manually provided, 
and the chance to set a optional instruction statement to include 
in every request. 

After completing these steps, your `smah` tool will be configured and ready to use.

### 3. Fine Tuning
You can tweak model setting rules/weighthing currently by 
manually editing the generated `~/.smah/config.yaml` file. 
You can try differnt config options out with the `--config` arg


```yaml 
vsn: 0.0.1
user:
  vsn: 0.0.1
  name: Your Name
  system_admin_experience: Intermediate
  role: Administrator
  about: |
    I prefer detailed responses. I am well versed in biology, mathematics, and software testing and engineering, as well as relational database design and tuning. I am an INTP personality type.
system:
  vsn: 0.0.1
  operating_system:
    type: Linux
    name: posix
    version: '#1 SMP Thu Oct 5 21:02:42 UTC 2023'
    release: 5.15.133.1-microsoft-standard-WSL2
    info:
      vsn: 0.0.1
      kind: Linux
      source: os-release
      details:
        bug-report-url: https://bugs.launchpad.net/ubuntu/
        home-url: https://www.ubuntu.com/
        id: ubuntu
        id-like: debian
        name: Ubuntu
        pretty-name: Ubuntu 22.04.4 LTS
        privacy-policy-url: https://www.ubuntu.com/legal/terms-and-policies/privacy-policy
        support-url: https://help.ubuntu.com/
        ubuntu-codename: jammy
        version: 22.04.4 LTS (Jammy Jellyfish)
        version-codename: jammy
        version-id: '22.04'
    vsn: 0.0.1
inference:
  vsn: 0.0.1
  instructions: null # Optional additional instructions to include in each request.
  model_picker:
    default:
    - openai.gpt-4o-mini
    - openai.gpt-4o
  providers:
    openai:
      name: OpenAI
      description: OpenAI Models
      enabled: true
      vsn: 0.0.1
      settings: {}
      models:
      - name: gpt-4-turbo
        model: gpt-4-turbo
        description: GPT-4 Turbo
        enabled: false
        training_cutoff: 2023-12-01 00:00:00
        license: OpenAI License
        model_type: LLM
        context:
          window: 128000
          out: 4096
        strengths:
        - Highly accurate
        - Fast
        weaknesses:
        - Expensive
        - Multimodal capabilities limited
        modalities:
          text:
            in: true
            out: true
          image:
            in: true
            out: false
        settings: {}
        attributes:
          speed: 5
          reasoning: 5
          planning: 5
          creativity: 5
          conciseness: 5
          coding: 5
        cost:
          million_tokens_in: 10.0
          million_tokens_out: 30.0
        use_cases:
        - name: Code Generation
          score: 0.5
        - name: Text Generation
          score: 0.6
        - name: Translation
          score: 0.5
        - name: Planning
          score: 0.5
        - name: Reasoning
          score: 0.5
        - name: Creativity
          score: 0.5
        - name: Data Analysis
          score: 0.5
        vsn: 0.0.1
# ...        
      - name: o1-mini
        model: o1-mini
        description: o1 (mini)
        enabled: false
        training_cutoff: 2023-12-01 00:00:00
        license: OpenAI License
        model_type: LLM
        context:
          window: 128000
          out: 32768
        strengths:
        - Highly accurate
        - Advanced Reasoning
        weaknesses:
        - Expensive
        - Multimodal capabilities limited
        modalities:
          text:
            in: true
            out: true
        settings:
          max_completion_tokens: true
        attributes:
          speed: 5
          reasoning: 7
          planning: 7
          creativity: 4
          conciseness: 7
          coding: 7
        cost:
          million_tokens_in: 3.0
          million_tokens_out: 12.0
        use_cases:
        - name: Code Generation
          score: 0.7
        - name: Text Generation
          score: 0.7
        - name: Translation
          score: 0.7
        - name: Planning
          score: 0.7
        - name: Reasoning
          score: 0.7
        - name: Creativity
          score: 0.4
        - name: Data Analysis
          score: 0.7
        vsn: 0.0.1

```

# Security
Do not pass sensitive data/details to Smah if your LLM will persist/track it, use a (pending) local model instead.
Double check exec commands they may have errors and require edits prior to execution. 

## Future Enhancements

SMAH is in its early alpha stage, and we are actively working on the following enhancements:

1. **Expanded Command Generation Use Cases**: Increase the range of commands that SMAH can generate, including more complex system operations and integrations with additional tools.
2. **Enhanced AI-Assisted Monitoring**: Improve the AI's ability to set up and manage system monitoring tasks, including more advanced metrics and alerting capabilities.
3. **Interactive Rich Terminal Interface**: Develop a terminal-based user interface for managing and interacting with the system, providing a richer user experience.
4. **Multi-User Support**: Implement support for multiple user accounts with shared global configuration options, allowing for seamless management across different users.
5. **Advanced Security Features**: Strengthen security measures, especially when running commands with elevated privileges, and enhance guardrail enforcement.
6. **Integration with External Tools**: Enable integration with other popular tools and services to streamline workflows and improve productivity.
7. **Data Visualization**: Add capabilities for visualizing data trends and analysis results, making it easier to interpret and present findings.
8. **Automated Reporting**: Develop features for generating automated reports based on data analyses, saving time on repetitive tasks.
9. **Enhanced Logging and Monitoring**: Improve the logging and monitoring system to provide more detailed insights and better auditability.
10. **Secrets Management**: Implement secure storage and management of sensitive information, such as API keys and passwords.

## 1-Year Roadmap

### Q1
- **Release Beta Version**: Transition from alpha to beta, incorporating initial user feedback and stabilizing core features.
- **Expand Command Generation**: Add support for more complex commands and integrations with additional tools.
- **Improve AI-Assisted Monitoring**: Enhance the AI's capabilities for setting up and managing system monitoring tasks.

### Q2
- **Develop Interactive Terminal Interface**: Create a rich terminal-based user interface for better user interaction.
- **Implement Multi-User Support**: Enable support for multiple user accounts with shared global configuration options.
- **Strengthen Security Features**: Enhance security measures, especially for commands requiring elevated privileges.

### Q3
- **Integrate with External Tools**: Enable seamless integration with other popular tools and services.
- **Add Data Visualization**: Develop features for visualizing data trends and analysis results.
- **Automate Reporting**: Implement automated reporting capabilities to save time on repetitive tasks.

### Q4
- **Enhance Logging and Monitoring**: Improve the logging and monitoring system for better insights and auditability.
- **Implement Secrets Management**: Develop secure storage and management of sensitive information.
- **Prepare for General Availability**: Finalize features and prepare for a general availability release, ensuring stability and robustness.

# Contributing

We welcome contributions to help improve SMAH. Here are some guidelines to get you started:

## How to Contribute

### Feature Requests, Feedback and Bug Reports

- Use the GitHub issues tracker to report bugs or suggest features.
- Provide as much detail as possible, including steps to reproduce the issue.
_ When use user-story style at the openning of feature/change requests.

### Bug Fixes and Code Changes
 
1. Fork the Repository: Create a personal fork of the repository on GitHub.
2. Create a Feature: Create a new branch for your feature or bugfix.
3. Make Changes: Make your changes in the new branch.
4. Commit Changes: Use descriptive commit changes orgnanize work, 
   rebase/group related items together for complex multi part changes
   and split into sub branches/pull requests. 
5. Make A Pull Request - give details on what you've changed/fixed.

### Code Style

- When Possible Follow the existing code style and conventions unless overhauling format/layout only (I suggest asking first.) 
- Write clear, concise, and descriptive commit messages.
- Use Type Hints and Doc Tags. 
- Ensure your code is well-documented. Consider md and mermaid diagrams for complax/major changes.

### Testing

- Write pytests for any new features or bug fixes.
- Ensure all tests pass before submitting a pull request.


## Code of Conduct

Be Kind.

# License
[MIT](./LICENSE)
