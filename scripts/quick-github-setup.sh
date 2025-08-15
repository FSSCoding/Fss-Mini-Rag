#!/bin/bash
# Quick GitHub Setup with Auto-Update Template
# One-command setup for converting projects to GitHub with auto-update

set -e

# Colors for better UX
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_help() {
    echo -e "${BOLD}Quick GitHub Setup with Auto-Update Template${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS] <project_path>"
    echo ""
    echo "Options:"
    echo "  -o, --owner OWNER       GitHub username/organization (required)"
    echo "  -n, --name NAME         Repository name (required)"
    echo "  -t, --type TYPE         Project type (python|general, default: python)"
    echo "  --no-auto-update        Disable auto-update system"
    echo "  --no-push              Don't push to GitHub automatically"
    echo "  -h, --help              Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 . -o myusername -n my-project"
    echo "  $0 /path/to/project -o myorg -n cool-tool --type python"
    echo "  $0 existing-project -o me -n project --no-auto-update"
    echo ""
}

main() {
    local project_path=""
    local repo_owner=""
    local repo_name=""
    local project_type="python"
    local auto_update=true
    local auto_push=true
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -o|--owner)
                repo_owner="$2"
                shift 2
                ;;
            -n|--name)
                repo_name="$2"
                shift 2
                ;;
            -t|--type)
                project_type="$2"
                shift 2
                ;;
            --no-auto-update)
                auto_update=false
                shift
                ;;
            --no-push)
                auto_push=false
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -*)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
            *)
                if [ -z "$project_path" ]; then
                    project_path="$1"
                else
                    echo -e "${RED}❌ Multiple project paths specified${NC}"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Validate required arguments
    if [ -z "$project_path" ]; then
        echo -e "${RED}❌ Project path required${NC}"
        show_help
        exit 1
    fi
    
    if [ -z "$repo_owner" ]; then
        echo -e "${RED}❌ GitHub owner required (use -o/--owner)${NC}"
        show_help
        exit 1
    fi
    
    if [ -z "$repo_name" ]; then
        echo -e "${RED}❌ Repository name required (use -n/--name)${NC}"
        show_help
        exit 1
    fi
    
    # Convert to absolute path
    project_path=$(realpath "$project_path")
    
    if [ ! -d "$project_path" ]; then
        echo -e "${RED}❌ Project directory does not exist: $project_path${NC}"
        exit 1
    fi
    
    echo -e "${BOLD}${CYAN}🚀 Quick GitHub Setup${NC}"
    echo -e "${BOLD}===================${NC}"
    echo ""
    echo -e "📁 Project: ${BOLD}$project_path${NC}"
    echo -e "👤 Owner: ${BOLD}$repo_owner${NC}"
    echo -e "📦 Repository: ${BOLD}$repo_name${NC}"
    echo -e "🔧 Type: ${BOLD}$project_type${NC}"
    echo -e "🔄 Auto-update: ${BOLD}$([ "$auto_update" = true ] && echo "Enabled" || echo "Disabled")${NC}"
    echo -e "🚀 Auto-push: ${BOLD}$([ "$auto_push" = true ] && echo "Enabled" || echo "Disabled")${NC}"
    echo ""
    
    # Confirm with user
    read -p "Continue with setup? [Y/n]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
        echo "Setup cancelled."
        exit 0
    fi
    
    cd "$project_path"
    
    # Step 1: Setup template
    echo -e "${YELLOW}[1/6]${NC} Setting up GitHub template..."
    
    python_script="$SCRIPT_DIR/setup-github-template.py"
    if [ ! -f "$python_script" ]; then
        echo -e "${RED}❌ Setup script not found: $python_script${NC}"
        exit 1
    fi
    
    local setup_args="$project_path --owner $repo_owner --name $repo_name --type $project_type"
    if [ "$auto_update" = false ]; then
        setup_args="$setup_args --no-auto-update"
    fi
    
    if ! python "$python_script" $setup_args; then
        echo -e "${RED}❌ Template setup failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Template setup completed${NC}"
    
    # Step 2: Initialize git if needed
    echo -e "${YELLOW}[2/6]${NC} Checking git repository..."
    
    if [ ! -d ".git" ]; then
        echo "Initializing git repository..."
        git init
        git branch -M main
    fi
    
    echo -e "${GREEN}✅ Git repository ready${NC}"
    
    # Step 3: Add and commit changes
    echo -e "${YELLOW}[3/6]${NC} Committing template changes..."
    
    git add .
    if git diff --cached --quiet; then
        echo "No changes to commit"
    else
        git commit -m "🚀 Add GitHub template with auto-update system

- Added GitHub Actions workflows (CI, release, template-sync)
- Integrated auto-update system for seamless updates
- Created issue templates and project configuration  
- Setup automated release and testing pipelines

Generated with FSS GitHub Template System"
    fi
    
    echo -e "${GREEN}✅ Changes committed${NC}"
    
    # Step 4: Setup GitHub remote if needed
    echo -e "${YELLOW}[4/6]${NC} Setting up GitHub remote..."
    
    github_url="https://github.com/$repo_owner/$repo_name.git"
    
    if ! git remote get-url origin >/dev/null 2>&1; then
        git remote add origin "$github_url"
        echo "Added GitHub remote: $github_url"
    else
        existing_url=$(git remote get-url origin)
        if [ "$existing_url" != "$github_url" ]; then
            echo "Warning: Origin remote exists with different URL: $existing_url"
            echo "Expected: $github_url"
            read -p "Update remote to GitHub? [Y/n]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
                git remote set-url origin "$github_url"
                echo "Updated remote to: $github_url"
            fi
        else
            echo "GitHub remote already configured"
        fi
    fi
    
    echo -e "${GREEN}✅ GitHub remote configured${NC}"
    
    # Step 5: Create GitHub repository (if possible)
    echo -e "${YELLOW}[5/6]${NC} Creating GitHub repository..."
    
    if command -v gh >/dev/null 2>&1; then
        # Check if repo exists
        if ! gh repo view "$repo_owner/$repo_name" >/dev/null 2>&1; then
            echo "Creating GitHub repository..."
            if gh repo create "$repo_owner/$repo_name" --private --source=. --remote=origin --push; then
                echo -e "${GREEN}✅ GitHub repository created and pushed${NC}"
                auto_push=false  # Already pushed
            else
                echo -e "${YELLOW}⚠️ Failed to create repository with gh CLI${NC}"
                echo "You'll need to create it manually at: https://github.com/new"
            fi
        else
            echo "Repository already exists on GitHub"
        fi
    else
        echo -e "${YELLOW}⚠️ GitHub CLI (gh) not installed${NC}"
        echo "Please create the repository manually at: https://github.com/new"
        echo "Repository name: $repo_name"
    fi
    
    # Step 6: Push to GitHub
    if [ "$auto_push" = true ]; then
        echo -e "${YELLOW}[6/6]${NC} Pushing to GitHub..."
        
        if git push -u origin main; then
            echo -e "${GREEN}✅ Pushed to GitHub${NC}"
        else
            echo -e "${YELLOW}⚠️ Push failed - you may need to create the repository first${NC}"
            echo "Create it at: https://github.com/$repo_owner/$repo_name"
        fi
    else
        echo -e "${YELLOW}[6/6]${NC} Skipping auto-push"
    fi
    
    # Success summary
    echo ""
    echo -e "${BOLD}${GREEN}🎉 Setup Complete!${NC}"
    echo -e "${BOLD}================${NC}"
    echo ""
    echo -e "📦 Repository: ${BLUE}https://github.com/$repo_owner/$repo_name${NC}"
    echo ""
    echo -e "${BOLD}🚀 Next Steps:${NC}"
    echo "1. Create your first release:"
    echo -e "   ${CYAN}git tag v1.0.0 && git push --tags${NC}"
    echo ""
    echo "2. Test auto-update system:"
    echo -e "   ${CYAN}./$repo_name check-update${NC}"
    echo ""
    echo "3. View GitHub Actions:"
    echo -e "   ${BLUE}https://github.com/$repo_owner/$repo_name/actions${NC}"
    echo ""
    if [ "$auto_update" = true ]; then
        echo -e "${BOLD}🔄 Auto-Update Enabled:${NC}"
        echo "   • Users will get update notifications automatically"
        echo "   • Updates install with one command"
        echo "   • Safe backup and rollback included"
        echo ""
    fi
    echo -e "💡 ${BOLD}Pro Tip:${NC} Future releases will automatically notify users!"
    echo ""
}

# Run main function
main "$@"