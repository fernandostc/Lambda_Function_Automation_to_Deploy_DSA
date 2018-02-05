import boto3
import os
import json

def lambda_handler(event, context):

    #get Instance-ID from the instance that generated the log in CloudWatch
    instanceid = event['detail']['instance-id']

    #Wait Instance to be with status Running
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instanceid)
    instance.wait_until_running()

    #Wait Instance to be with Status check to be ready (2/2)
    ec2client = boto3.client('ec2')
    waiter = ec2client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instanceid])

    #get the IAM (Arn) applied for the instance
    ARN = instance.iam_instance_profile

    if ARN == None:
        #Get values from Environment variables created on CloudFormation process
        ARNInstancePro = os.environ['InstanceProfiletoEC2Arn']
        NameInstancePro = os.environ['InstanceProfiletoEC2Name']

        #Apply one InstanceProfile/Role to the EC2
        ARNResponse = ec2client.associate_iam_instance_profile(
            IamInstanceProfile={
                'Arn': ARNInstancePro,
                'Name': NameInstancePro
            },
            InstanceId=instanceid
        )

    else:

        #get just the ARN Name
        role = os.environ['NameRole']

        #Get the Policy ARN that was create by the cloudformation
        roles = os.environ['NameRole']
        clientiam = boto3.client('iam')
        responseiam = clientiam.list_attached_role_policies(
        RoleName= roles,
        PathPrefix='/',
        )

        PolicyArnSSM = responseiam['AttachedPolicies'][0]['PolicyArn']

        #Attach a policy in one existing Role
        client = boto3.client('iam')
        response = client.attach_role_policy(
        PolicyArn=PolicyArnSSM,
        RoleName=role,
        )

    #Run Document for the instance to deploy and activate DS agent
    EC2id = [instanceid]
    NameDocument = os.environ['LinuxDocument']
    ssm = boto3.client('ssm')
    testCommand = ssm.send_command(InstanceIds=EC2id, DocumentName=NameDocument)

    return 0
