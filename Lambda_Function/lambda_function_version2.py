import boto3
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.info("logging setup complete")
#logging.getLogger('botocore').setLevel(logging.DEBUG)
#logging.getLogger('boto3').setLevel(logging.DEBUG)

def lambda_handler(event, context):
    logger.info('initializing for instanceid: ' + event['detail']['instance-id'])
    #get InstanceID from the EC2 that generated the log in CloudWatch
    instanceid = event['detail']['instance-id']

    #Wait EC2 to be with status Running
    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instanceid)
    instance.wait_until_running()

    #Wait Instance to be with Status check to be ready (2/2)
    ec2client = boto3.client('ec2')
    waiter = ec2client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instanceid])

    logger.info("instance " + instanceid + " is running with status ready 2/2")

    #get the IAM (Arn) applied for the instance
    ARN = instance.iam_instance_profile

    checktag = 0

    #Check if the EC2 has the Tag InstallDSA if not add Tag Install DSA with Value 'Yes'
    if instance.tags == None:
        logger.info("instance " + instanceid + " has no tags; adding")
        #Call the function addTag
        addTag(ec2client, instanceid)
    else:
        #Check if there are any Tag associated with the Ec2 with the name InstallDSA and with the Value set up as "No" or "no", if yes stop the script
        for tags in instance.tags:
            if tags['Key'] == "InstallDSA":
                if (tags["Value"] == 'No') or (tags["Value"] == 'no'):
                    logger.info("instance " + instanceid + " has tag InstallDSA == no; aborting")
                    checktag = 1
                    return 0

    if checktag == 0:
        addTag(ec2client, instanceid)

    if ARN == None:
        #Get values from Environment variables created by the CloudFormation process
        ARNInstancePro = os.environ['InstanceProfiletoEC2Arn']
        NameInstancePro = os.environ['InstanceProfiletoEC2Name']
        logger.info("instance " + instanceid + " has no instance profile; fixing it with " + ARNInstancePro + " named " + NameInstancePro)
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
        logger.info("instance " + instanceid + " has an instance profile; attaching SSM policy")
        PolicyArnSSM = responseiam['AttachedPolicies'][0]['PolicyArn']

        #Attach a policy in one existing Role
        client = boto3.client('iam')
        response = client.attach_role_policy(
        PolicyArn=PolicyArnSSM,
        RoleName=role,
        )
        logger.info("instance " + instanceid + " response from role attach: " + response)

    return 0

def addTag(ec2object,ec2id):
    #Use function from boto3 to add Tag to the EC2
    logger.info("instance " + ec2id + " is getting the InstallDSA tag")
    response = ec2object.create_tags(
                Resources=[
                    ec2id,
                ],
                Tags=[
                    {
                        'Key': 'InstallDSA',
                        'Value': 'Yes'
                    },
                ]
            )
