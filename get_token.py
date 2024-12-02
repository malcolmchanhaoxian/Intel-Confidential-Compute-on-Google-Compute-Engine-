from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/run-command', methods=['POST'])
def get_token():
    """
    Endpoint to execute the trustauthority-cli command with optional policy-id and match-policy flags.
    """
    # Parse JSON input from client
    data = request.json
    policy_id = data.get("policy-id", "").strip()
    match_policy = data.get("match-policy", False)  # Default to False

    # Base command
    command = ['trustauthority-cli', 'token', '-c', 'config.json', '--tdx', 'true']

    # Add policy-id if provided
    if policy_id:
        command.extend(['--policy-ids', policy_id])

    # Add '--policy-must-match' if match_policy is true
    if match_policy:
        command.append('--policy-must-match')

    try:
        # Run the command using subprocess
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Parse and format the output as JSON, if applicable
        try:
            output_data = json.loads(result.stdout)
            return jsonify({
                "status": "success",
                "data": output_data
            }), 200
        except json.JSONDecodeError:
            # If output is not JSON, return as plain text
            return jsonify({
                "status": "success",
                "data": result.stdout
            }), 200

    except subprocess.CalledProcessError as e:
        # Handle error if the command fails
        return jsonify({
            "status": "error",
            "message": e.stderr.strip()
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)