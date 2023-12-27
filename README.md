# aergi
CLI Client for Tempo Timesheets in Jira


# System Requirements
* Python 3.9 or later
* Python Modules:
  * prettytable
  * requests
  * pyyaml

## Prerequisites

Aergi uses the following environment variables: 

```bash
export AERGI_HOME= # Path to aergi repo
export PATH=$AERGI_HOME/bin:$PATH
export PYTHONPATH=$AERGI_HOME/lib:$PYTHONPATH
export JIRA_TOKEN= # A valid Jira API token - see instructions below
export AERGI_PROJECT=foo # name of Jira/Tempo project
export AERGI_WORKER=jdoe # Only necessary if differs from $LOGNAME
```

To create a Jira Personal Access Token:

1. Navigate to Jira - Personal Access Tokens page
2. Click on "Create token"
3. Provide token name and expiration date
4. Click "Create"



# Usage

*tl;dr* Log a day's work in a YAML file (ex. work-log.yaml):

```yaml
2023-12-04:
- 5.5 FOO-1 working hard
- 2.5 FOO-2 hardly working
```

and log them:

```bash
aergi log -i work-log.yaml
```

### Get existing time entries
```bash
aergi get --from 2023-02-01 --to 2023-03-01
```
### Log/set new time entries
```bash
aergi log -i 2023-02-24.yaml
```
### Create template file for the current week
```bash
aergi create
```
### Set input file default
```bash
aergi config --input 2023-03-03.yaml
```
### Edit currently defaulted file
```bash
aergi edit
aergi vi
```

## Setting up your Work Log

`aergi log` will process and log time from a YAML input file containing your work log. For formatting, refer to the following example:

```yaml
2023-02-19:
- 5.5 FOO-1 working hard
- 2.5 FOO-2 hardly working
```

Each object represents a calendar date in yyyy-MM-dd format, and each attribute within corresponds to a work log for that date. 

Work log format is as follows:


`- [hours] [issue] [summary]`

- `hours`: a decimal number (e.g. 1.0) indicating how much time was spent in hours working on the issue
- `issue`: the Jira issue number (e.g. FOO-1) for which the time will be logged
- `summary`: a summary of the work for the log

Aergi will process each log item, creating a request containing the required fields to log time in Tempo, and send the request to the Jira API.

Aergi also supports passing individual work logs in stdin.

## Configuring JIRA/Tempo projects

Aergi supports custom JSON configurations for Jira issues, Tempo projects, and (optionally) activities. Defaults are stored in the `config` directory and are intended for Tempo field mappings, common org-level options etc. See below for supported configurations:


`issues.json` - Default summaries for time logged against Tempo projects:

```json
{
  "TEMPO-1": "PTO",
  "TEMPO-2": "Holiday",
  "TEMPO-3": "Sick",
  "TEMPO-4": "Management",
  "TEMPO-5": "Non-Project Meetings / General Status"
}
```

`activity.json` - Default shorthand mappings of global activity fullnames

```json
{
  "example": "Activity Name in JIRA",
  "design": "Design",
  "dev": "Development",
  "test": "Testing",
  "plan": "Planning",
  "non-proj": "Non-project time"
}
```

`work.json` - Default shorthand mappings of issues and activities:

```json
{
  "pto":           { "issue": "TEMPO-1",       "activity": "pto" },
  "holiday":       { "issue": "TEMPO-2",       "activity": "holiday" },
  "sick":          { "issue": "TEMPO-3",       "activity": "sick" },
  "management":    { "issue": "TEMPO-4",       "activity": "manage" },
  "team":          { "issue": "TEMPO-5",       "activity": "non-proj" },
  "daily":         { "issue": "TEMPO-5",       "activity": "non-proj" },
  "interview":     { "issue": "TEMPO-5",       "activity": "non-proj" },
  "non-proj":      { "issue": "TEMPO-5",       "activity": "non-proj" },

  "support":       { "issue": "SUPPORT-1",     "activity": "support", "note": "general support" },
  "secret-dev":    { "issue": "SECRET-1",      "activity": "dev" }
}
```

Once the defaults are set, any relevant issues and summary can then be replaced with the shorthand in the work log. For example:

```yaml
2023-02-20:
- 8.0 holiday
```
### work-custom.json

In addition to the default configs, Aergi accepts a custom user-scoped config file called `work-custom.json`. If present, any additional mappings specified in the file will be loaded and available for use. This file can be present in the current directory of where you are running `aergi`.

```json
{
  "foo":     { "issue": "FOO-1", "summary": "hello" },
  "bar":     { "issue": "FOO-2", "summary": "world" },
  "foobar":  { "issue": "FOO-3", "summary": "hello world" },
  "demo":    { "issue": "BAR-1", "summary": "demo" },
  "meeting": { "issue": "BAR-2", "summary": "i hate meetings" }
}
```

Work log:

```yaml
2023-02-20:
- 8.0 holiday

2023-02-21:
- 1.0 meeting stupid dumb meeting
- 5.0 foo implementing feature
- 2.0 bar bugfix

2023-02-22:
- 7.0 demo crunch time
- 1.0 meeting another one?

...
```

This is included as a convenient way for users to further customize their configs and change shorthands at their discretion.

## Searching Jira
```bash
# NOTE: Make sure to set the AERGI_PROJECT env var for the project default to change to your Jira project

# Find all issues under your project with "foo" in the summary
js -s foo

# Find epic issues under your project with "foo" in the summary
js -e -s foo

# Run a custom jql
js -j 'summary ~ "test1"'
```

# Notes & Issues
* The script will error out with 403 if a change is attempted for time period already approved by the approver
