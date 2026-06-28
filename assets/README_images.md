# Image Assets for `replace_placeholder_images`.

This project uses local candidate images (downloaded from appropriate sources) to ensure:
- uniqueness by SHA-256
- deterministic resizing/optimization
- no dependency on external sites during the Django command

## Folder structure (required)

```text
assets/
├── provider_headshots/
│   ├── *.jpg
│   ├── *.png
│   └── ...
└── service_images/
    ├── plumbing/
    ├── electrician/
    ├── carpenter/
    ├── cleaning/
    ├── painting/
    ├── ac-repair/
    ├── appliance-repair/
    ├── gardening/
    └── ...
```

## Category mapping
The command does **not** hardcode category names.
For each `Service.category.name`, it normalizes into a slug:
- lowercase
- trim whitespace
- replace spaces with `-`
- replace `&` with `and`
- remove unsupported characters

Then it looks for `assets/service_images/<slug>/`.

Example:
- `AC Repair` -> `ac-repair`
- `Appliance Repair` -> `appliance-repair`
- `Cleaner` -> `cleaner` (make sure folder name matches the normalized slug)

## Minimum counts
The command will fail if there aren’t enough provider images to cover the target `--provider-count`.
For services, if a category folder doesn’t exist or doesn’t have enough unique candidates, only the available services for that category are updated.

## Licensing
Ensure the images you place here are free/licensed for reuse in a project.

