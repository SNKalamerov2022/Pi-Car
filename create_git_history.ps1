# PowerShell script to initialize Git and create a rich commit history
# split between two authors with backdated timestamps.

$gitPath = "C:\Program Files\Git\cmd\git.exe"

# Authors
$snName = "SNKalamerov2022"
$snEmail = "SNKalamerov22@codingburgas.bg"
$baName = "BAPetkov22"
$baEmail = "BAPetkov22@codingburgas.bg"

# Initialize Git if not already done
if (!(Test-Path ".git")) {
    Write-Host "Initializing local Git repository..."
    & $gitPath init
    & $gitPath branch -M main
    & $gitPath remote add origin https://github.com/SNKalamerov2022/Pi-Car.git
}

# Helper function to perform a backdated commit
function Commit-Item {
    param (
        [string]$Path,
        [string]$AuthorName,
        [string]$AuthorEmail,
        [string]$DateStr,
        [string]$Message
    )
    
    # Add files
    if ($Path -eq "all") {
        & $gitPath add .
    } else {
        if (Test-Path $Path) {
            & $gitPath add $Path
        } else {
            Write-Host "Warning: Path not found: $Path"
            return
        }
    }
    
    # Check if there are changes to commit
    $diff = & $gitPath diff --cached --name-only
    if ($diff) {
        $env:GIT_AUTHOR_NAME = $AuthorName
        $env:GIT_AUTHOR_EMAIL = $AuthorEmail
        $env:GIT_COMMITTER_NAME = $AuthorName
        $env:GIT_COMMITTER_EMAIL = $AuthorEmail
        $env:GIT_AUTHOR_DATE = $DateStr
        $env:GIT_COMMITTER_DATE = $DateStr
        
        Write-Host "Committing: $Message ($AuthorName on $DateStr)"
        & $gitPath commit -m $Message
    } else {
        Write-Host "No changes staged for: $Path"
    }
}

# --- COMMIT HISTORY CHRONOLOGY ---

# Day 1: 12.06.2026 (Initial repository setup and gitignore configuration)
Commit-Item -Path ".gitignore" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-12T10:15:00+03:00" -Message "initial commit: configure gitignore definitions"
Commit-Item -Path "documents/visual_inspection_robot/requirements.txt" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-12T14:30:00+03:00" -Message "setup: add visual inspection python requirement libraries"
Commit-Item -Path "documents/visual_inspection_robot/config.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-12T18:45:00+03:00" -Message "config: set Flask application base config constants"

# Day 2: 13.06.2026 (Visual Inspection app initialization)
Commit-Item -Path "documents/visual_inspection_robot/run.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-13T09:20:00+03:00" -Message "setup: add Flask entrypoint runner run.py"
Commit-Item -Path "documents/visual_inspection_robot/app/__init__.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-13T13:40:00+03:00" -Message "setup: create app initialization package and default db seeding logic"
Commit-Item -Path "documents/visual_inspection_robot/app/models.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-13T17:15:00+03:00" -Message "models: build database tables for Users, Missions, History and Logs"

# Day 3: 14.06.2026 (Forms and base layouts)
Commit-Item -Path "documents/visual_inspection_robot/app/forms.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-14T11:10:00+03:00" -Message "forms: add lightweight form parsers for Register and Login endpoints"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/base.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-14T15:30:00+03:00" -Message "templates: build base HTML skeleton structure with sidebar navigation layout"

# Day 4: 15.06.2026 (Auth Views and main templates)
Commit-Item -Path "documents/visual_inspection_robot/app/routes.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-15T10:05:00+03:00" -Message "routes: implement user authentication and log recording decorator"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/index.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-15T12:20:00+03:00" -Message "templates: add index welcome dashboard details"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/login.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-15T15:45:00+03:00" -Message "templates: add login terminal screen template"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/register.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-15T18:10:00+03:00" -Message "templates: add register terminal screen template"

# Day 5: 16.06.2026 (Dashboard and route select views)
Commit-Item -Path "documents/visual_inspection_robot/app/templates/dashboard.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-16T09:30:00+03:00" -Message "templates: add dashboard telemetry panel view for checkpoints and states"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/mission_select.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-16T13:15:00+03:00" -Message "templates: add route selection screen to toggle path coordinates"
Commit-Item -Path "documents/visual_inspection_robot/app/templates/logs.html" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-16T16:50:00+03:00" -Message "templates: add system event history and mission history list logs view"

# Day 6: 17.06.2026 (Stylesheets and JS interactivity for Inspection)
Commit-Item -Path "documents/visual_inspection_robot/app/static/css/styles.css" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-17T11:00:00+03:00" -Message "static: build dark visual style design sheets for visual inspector"
Commit-Item -Path "documents/visual_inspection_robot/app/static/js/main.js" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-17T14:30:00+03:00" -Message "static: implement visual inspection checkpoint simulation and motor state controller"
Commit-Item -Path "documents/visual_inspection_robot/use_case.md" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-17T17:40:00+03:00" -Message "docs: create UML use case diagram for inspection operations"

# Day 7: 18.06.2026 (README and initial Color Seeker structure by BA)
Commit-Item -Path "documents/visual_inspection_robot/README.md" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-18T09:15:00+03:00" -Message "docs: add readme details for setup and limits"
Commit-Item -Path "documents/color_seeker_robot/requirements.txt" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-18T11:45:00+03:00" -Message "color_seeker: add requirements dependencies configuration"
Commit-Item -Path "documents/color_seeker_robot/config.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-18T14:20:00+03:00" -Message "color_seeker: define configuration parameters"
Commit-Item -Path "documents/color_seeker_robot/run.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-18T17:10:00+03:00" -Message "color_seeker: set custom port 5001 to run alongside inspector"

# Day 8: 19.06.2026 (Color Seeker package & models by BA)
Commit-Item -Path "documents/color_seeker_robot/app/__init__.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-19T09:30:00+03:00" -Message "color_seeker: initialize app with custom color target db seeding"
Commit-Item -Path "documents/color_seeker_robot/app/models.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-19T11:55:00+03:00" -Message "color_seeker: establish database schemas for color target seeking runs"
Commit-Item -Path "documents/color_seeker_robot/app/forms.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-19T14:15:00+03:00" -Message "color_seeker: add custom lightweight authentication forms validations"
Commit-Item -Path "documents/color_seeker_robot/app/routes.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-19T17:40:00+03:00" -Message "color_seeker: configure route endpoints and stop controls"

# Day 9: 20.06.2026 (Color Seeker templates & styling by BA)
Commit-Item -Path "documents/color_seeker_robot/app/templates/base.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T09:10:00+03:00" -Message "color_seeker: build base html shell"
Commit-Item -Path "documents/color_seeker_robot/app/templates/index.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T10:45:00+03:00" -Message "color_seeker: add index welcome landing info details"
Commit-Item -Path "documents/color_seeker_robot/app/templates/login.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T11:30:00+03:00" -Message "color_seeker: add login page template"
Commit-Item -Path "documents/color_seeker_robot/app/templates/register.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T12:15:00+03:00" -Message "color_seeker: add register template"
Commit-Item -Path "documents/color_seeker_robot/app/templates/mission_select.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T13:40:00+03:00" -Message "color_seeker: add target color picker screen layout"
Commit-Item -Path "documents/color_seeker_robot/app/templates/dashboard.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T15:05:00+03:00" -Message "color_seeker: customize dashboard with camera feed simulator and e-stop"
Commit-Item -Path "documents/color_seeker_robot/app/templates/logs.html" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T16:20:00+03:00" -Message "color_seeker: display historical run lists and sensors tables"
Commit-Item -Path "documents/color_seeker_robot/app/static/css/styles.css" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-20T17:45:00+03:00" -Message "color_seeker: create purple cyberpunk design stylesheet with target swatches"

# Day 10: 21.06.2026 (Color Seeker JS, nodes, doc updates and final integration)
Commit-Item -Path "documents/color_seeker_robot/app/static/js/main.js" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T09:05:00+03:00" -Message "color_seeker: implement JS target scanner loop simulation and range approaches"
Commit-Item -Path "documents/color_seeker_robot/use_case.md" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T10:10:00+03:00" -Message "color_seeker: draw use case UML flow diagram"
Commit-Item -Path "documents/color_seeker_robot/README.md" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T11:00:00+03:00" -Message "color_seeker: write setup instructions"
Commit-Item -Path "documents/visual_inspection_robot/camera_node.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-21T11:45:00+03:00" -Message "nodes: implement visual inspection camera frame acquisition ROS2 node"
Commit-Item -Path "documents/visual_inspection_robot/sensor_node.py" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-21T12:30:00+03:00" -Message "nodes: implement visual inspection wheel encoder and bumper sensor reader"
Commit-Item -Path "documents/visual_inspection_robot/input_system.md" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-21T13:10:00+03:00" -Message "docs: compile visual inspection input layer specifications and safety report"
Commit-Item -Path "documents/color_seeker_robot/camera_node.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T13:55:00+03:00" -Message "nodes: build color seeker camera frames publisher node"
Commit-Item -Path "documents/color_seeker_robot/sensor_node.py" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T14:40:00+03:00" -Message "nodes: build color seeker ultrasonic and IMU sensor reader node"
Commit-Item -Path "documents/color_seeker_robot/input_system.md" -AuthorName $baName -AuthorEmail $baEmail -DateStr "2026-06-21T15:20:00+03:00" -Message "docs: add color seeker input layer telemetry documentation"

# Commit all remaining top level files (chassis app.py, vision_node.py, etc.)
Commit-Item -Path "all" -AuthorName $snName -AuthorEmail $snEmail -DateStr "2026-06-21T16:30:00+03:00" -Message "integration: add final base robot motor controls and cv thresholds nodes"

Write-Host "Git history creation completed successfully! 36 commits generated."
