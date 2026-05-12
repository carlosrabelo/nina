import os
import glob

replacements = {
    "email_learning.service": "email_label.interpreter",
    "email_learning": "email_label",
    "emailtag": "email_label",
    "handle_emailtag": "handle_email_label",
    "do_emailtag": "do_email_label",
    "help_emailtag": "help_email_label",
    "emailtag.suggest_telegram": "email_label.suggest_telegram",
}

files_to_check = []
for root, _, files in os.walk("nina"):
    for file in files:
        if file.endswith(".py") or file.endswith(".md"):
            files_to_check.append(os.path.join(root, file))

for root, _, files in os.walk("."):
    for file in files:
        if file.endswith(".md") and "nina/" not in root:
            files_to_check.append(os.path.join(root, file))

for filepath in files_to_check:
    with open(filepath, "r") as f:
        content = f.read()
    
    new_content = content
    # Order matters: replace specific first
    for k in ["email_learning.service", "handle_emailtag", "do_emailtag", "help_emailtag", "emailtag.suggest_telegram", "emailtag", "email_learning"]:
        new_content = new_content.replace(k, replacements[k])
    
    # We should also replace 'email learning' to 'email label' in some comments? The user said "renomear a pasta para email_label e o comando também emailtag". So just the identifiers are fine.
    
    if new_content != content:
        with open(filepath, "w") as f:
            f.write(new_content)
        print(f"Updated {filepath}")
