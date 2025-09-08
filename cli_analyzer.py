import os
import re
import json
import argparse
import boto3
from git import Repo, InvalidGitRepositoryError
import datetime

def chunk_text(text, max_chars=2000):
    chunks = []
    for i in range(0, len(text), max_chars):
        chunks.append(text[i:i+max_chars])
    return chunks

def load_prompt(pillar, code):
    filename = pillar.lower().replace(" ", "_") + ".txt"
    path = os.path.join("prompts", filename)
    with open(path, "r") as f:
        template = f.read()
    return template.replace("{code}", code)

def analyze_with_bedrock(client, inference_profile_arn, text, pillar):
    prompt = load_prompt(pillar, text)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4000,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    }

    response = client.invoke_model(
        modelId=inference_profile_arn,   # ✅ use inference profile ARN
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json"
    )

    raw = response["body"].read().decode("utf-8")
    data = json.loads(raw)

    # Extract text
    text_out = "".join([c["text"] for c in data.get("content", []) if c["type"] == "text"])

    # Remove ```json fences
    clean_text = re.sub(r"^```json|```$", "", text_out.strip(), flags=re.MULTILINE).strip()

    # Try parsing JSON
    try:
        parsed = json.loads(clean_text)
    except Exception:
        parsed = {"issues": [{"description": clean_text, "severity": "UNKNOWN", "recommendation": "Check manually", "pillar": pillar}]}

    return parsed

def setup_repository(repo_url, clone_dir):
    """Setup repository - clone if doesn't exist, otherwise pull latest changes"""
    if os.path.exists(clone_dir):
        try:
            repo = Repo(clone_dir)
            print(f"Repository exists. Pulling latest changes...")
            origin = repo.remotes.origin
            origin.pull()
            print("Repository updated successfully.")
        except InvalidGitRepositoryError:
            print(f"Directory {clone_dir} exists but is not a git repository. Removing and cloning fresh...")
            import shutil
            shutil.rmtree(clone_dir)
            Repo.clone_from(repo_url, clone_dir)
            print("Repository cloned successfully.")
        except Exception as e:
            print(f"Error updating repository: {e}")
            print("Proceeding with existing files...")
    else:
        print(f"Cloning repository to {clone_dir}...")
        Repo.clone_from(repo_url, clone_dir)
        print("Repository cloned successfully.")

def main(profile):
    session = boto3.Session(profile_name=profile, region_name="us-west-2")
    client = session.client("bedrock-runtime")

    repo_url = "https://github.com/XI4684-AdithyaShankaran/microservices-demo.git"
    clone_dir = "./cloned_repo"

    setup_repository(repo_url, clone_dir)

    tf_dir = os.path.join(clone_dir, "infra", "aws-tf")
    if not os.path.exists(tf_dir):
        print(f"Terraform directory not found at {tf_dir}")
        return

    results = {}

    pillars = [
        "Operational Excellence",
        "Security", 
        "Reliability",
        "Performance Efficiency",
        "Cost Optimization",
        "Sustainability"
    ]

    
    inference_profile_arn = os.getenv("BEDROCK_INFERENCE_PROFILE_ARN", "arn:aws:bedrock:us-west-2:YOUR_ACCOUNT_ID:inference-profile/us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    print(f"Using inference profile: {inference_profile_arn}")

    print(f"Starting analysis of Terraform files in {tf_dir}")
    for root, _, files in os.walk(tf_dir):
        for file in files:
            if file.endswith(".tf"):
                print(f"Analyzing file: {file}")
                path = os.path.join(root, file)

                try:
                    with open(path, "r", encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading file {file}: {e}")
                    continue

                file_results = {}

                for pillar in pillars:
                    print(f"  Analyzing {pillar}...")
                    try:
                        # If content is too large, chunk it but analyze each chunk separately
                        if len(content) > 2000:
                            chunks = chunk_text(content)
                            pillar_results = []
                            for i, chunk in enumerate(chunks):
                                try:
                                    output = analyze_with_bedrock(client, inference_profile_arn, chunk, pillar)
                                    pillar_results.append(output)
                                except Exception as e:
                                    print(f"    Error analyzing chunk {i+1} for {pillar}: {e}")
                                    pillar_results.append({"error": str(e)})
                            file_results[pillar] = pillar_results
                        else:
                            # Analyze entire file content for this pillar
                            output = analyze_with_bedrock(client, inference_profile_arn, content, pillar)
                            file_results[pillar] = [output]
                    except Exception as e:
                        print(f"    Error analyzing {pillar}: {e}")
                        file_results[pillar] = [{"error": str(e)}]

                results[file] = file_results

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"results_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Analysis complete. Results saved to {results_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Terraform files using AWS Bedrock Claude 3.7 Sonnet via Inference Profile")
    parser.add_argument("--profile", required=True, help="AWS CLI profile name")
    parser.add_argument("--force-clone", action="store_true", help="Force fresh clone even if repo exists")
    args = parser.parse_args()

    if args.force_clone and os.path.exists("./cloned_repo"):
        import shutil
        shutil.rmtree("./cloned_repo")

    main(args.profile)
