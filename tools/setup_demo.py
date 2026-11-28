"""Run this ONCE in AWS CloudShell (region us-east-1). It needs no access keys: CloudShell uses
your console login. It creates:
  * an execution role for the demo functions
  * four demo Lambda functions (names start with ioc-demo-)
  * an extra inline policy for the IAM user used by the backend, limited to the ioc-demo-* functions
    (invoke / change configuration / change code) plus read access to Lambda log events.

Usage:   python3 setup_demo.py --user intelliopticloud-app
"""
import argparse
import io
import json
import time
import zipfile
from pathlib import Path

import boto3

ROLE = "ioc-demo-role"
FUNCTIONS = {            # name: initial memory (MB)
    "ioc-demo-bench": 512,    # used by collect_benchmark.py (memory is changed by the script)
    "ioc-demo-api": 1024,     # I/O-bound: waits for a database/API, over-provisioned
    "ioc-demo-compute": 2048, # CPU-bound
    "ioc-demo-heavy": 1024,   # needs about 750 MB: must NOT be reduced
}


def zip_handler() -> bytes:
    code = (Path(__file__).parent / "demo_handler.py").read_text()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("lambda_function.py", code)
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="intelliopticloud-app", help="IAM user of the backend")
    args = ap.parse_args()

    session = boto3.session.Session()
    region = session.region_name
    print("Region:", region)
    if region != "us-east-1":
        print("WARNING: the backend reads us-east-1. Switch CloudShell to N. Virginia and run again.")
        return
    account = session.client("sts").get_caller_identity()["Account"]
    iam, lam = session.client("iam"), session.client("lambda")

    # 1. execution role
    try:
        role_arn = iam.get_role(RoleName=ROLE)["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        trust = {"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
                 "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}
        role_arn = iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps(trust))["Role"]["Arn"]
        iam.attach_role_policy(RoleName=ROLE, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")
        print("Created role", ROLE, "- waiting 15 s for it to become usable")
        time.sleep(15)

    # 2. demo functions
    package = zip_handler()
    for name, mem in FUNCTIONS.items():
        try:
            lam.get_function(FunctionName=name)
            lam.update_function_code(FunctionName=name, ZipFile=package, Architectures=["x86_64"])
            lam.get_waiter("function_updated_v2").wait(FunctionName=name)
            lam.update_function_configuration(FunctionName=name, MemorySize=mem, Timeout=60)
            action = "updated"
        except lam.exceptions.ResourceNotFoundException:
            lam.create_function(FunctionName=name, Runtime="python3.12", Role=role_arn,
                                Handler="lambda_function.lambda_handler", Code={"ZipFile": package},
                                MemorySize=mem, Timeout=60, Architectures=["x86_64"])
            action = "created"
        lam.get_waiter("function_active_v2").wait(FunctionName=name)
        print(f"{action}: {name} ({mem} MB)")

    # 3. permissions for the backend user (only the demo functions can be changed)
    policy = {"Version": "2012-10-17", "Statement": [
        {"Sid": "ReadLambdaLogEvents", "Effect": "Allow",
         "Action": ["logs:FilterLogEvents", "logs:GetLogEvents", "logs:DescribeLogStreams"],
         "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/*:*"},
        {"Sid": "ManageDemoFunctionsOnly", "Effect": "Allow",
         "Action": ["lambda:InvokeFunction", "lambda:UpdateFunctionConfiguration", "lambda:UpdateFunctionCode",
                    "lambda:GetFunction", "lambda:GetFunctionConfiguration"],
         "Resource": f"arn:aws:lambda:*:{account}:function:ioc-demo-*"}]}
    iam.put_user_policy(UserName=args.user, PolicyName="IntelliOptiCloudDemoAccess", PolicyDocument=json.dumps(policy))
    print("Policy IntelliOptiCloudDemoAccess attached to user", args.user)
    print("Done.")


if __name__ == "__main__":
    main()
