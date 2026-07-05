
SFTP Job Scheduler Script Templates
These SFTP Job Scheduler Script templates help you set up SFTP transfers using the CFT SFTP scheduler. Choose the appropriate template based on whether you’re sending or receiving files.

SFTP Scheduler as Sender
SFTP Scheduler as Receiver
How to use these templates

These scripts are basic templates that you need to adjust for your specific use:

Check your zone settings

For Internet Zone (EZ): Look for comments with EZ or INTERNET
For Intranet Zone (IZ): Look for comments with IZ or INTRANET
Check your authentication method

For SSH Key only: Use the default settings
For SSH Key AND Password: Look for comments about “SSH Key AND Password”
Refer to the script comments

Comments in the script (lines starting with #) will guide you on what to change
Make changes only where the comments indicate
Important notes

If you have added customisations such as a Vanity ID or Custom Port, refer to Other requirements for the changes required.
When the File Archive feature is enabled, using the lcd command in your SFTP job script may result in incorrect file paths. To prevent this, avoid using the lcd command when File Archive is enabled.
SFTP Scheduler as Sender
This is a sample template for when you have an SFTP Server configured as Sender in your workflow.

# Updated: 16/08/24

#!/bin/bash
echo "=================================================="
echo "#### SFTP script execution started ####"
echo "=================================================="

printf "\n"

# Environment variables

echo "=================================================="
echo "#### Print env variables ####"
echo "SFTP_SERVER_HOSTNAME" ${SFTP_SERVER_HOSTNAME}
echo "SFTP_SERVER_USERNAME" ${SFTP_SERVER_USERNAME}
echo "SFTP_SERVER_AUTH_METHOD" ${SFTP_SERVER_AUTH_METHOD}
echo "SFTP_SERVER_PORT" ${SFTP_SERVER_PORT}
echo "WORKFLOW_ID" ${WORKFLOW_ID}
echo "=================================================="

printf "\n"

# Create INCOMING folder

echo "=================================================="
echo "#### Creating Temp Folder ####"
export INCOMING="INCOMING_`date +%Y%m%d`"
mkdir $INCOMING
echo "=================================================="

printf "\n"

# SFTP config

export PROXY="ProxyCommand nc -X connect -x cft2-prd-sftp-iz-proxy-nlb-c56328f1649d5d1b.elb.ap-southeast-1.amazonaws.com:3128 %h %p"
export HOST_KEY_ALGORITHM="-oHostKeyAlgorithms=+ssh-rsa"
export HOST_KEY_CHECK="-oStrictHostKeyChecking=no"
export PUB_KEY_ACCEPTED_KEY_TYPES="-o PubkeyAcceptedKeyTypes=+ssh-rsa"
export IDENTITY_FILE="-oIdentityFile=./id_rsa"

# PULL files from Agency/Partner SFTP server

echo "=================================================="
echo "#### Connect to SFTP Server and pull file ####"

# if auth method is "SSH Key AND Password"

# add "sshpass -e SFTP_SERVER_USER_PASSWORD" BEFORE "sftp ..." command

# e.g., "sshpass -e SFTP_SERVER_USER_PASSWORD sftp $ $ $ ..."

# if Sender Zone is INTERNET, uncomment below:

# sftp $ $ $ $ ${SFTP_SERVER_USERNAME}@$ <<EOF

sftp ${HOST_KEY_ALGORITHM} ${HOST_KEY_CHECK} ${PUB_KEY_ACCEPTED_KEY_TYPES} ${IDENTITY_FILE} -o "${PROXY}" ${SFTP_SERVER_USERNAME}@${SFTP_SERVER_HOSTNAME} <<EOF
lcd ./$INCOMING
get *
exit
EOF
echo "SFTP GET : " $?
echo "=================================================="

printf "\n"

echo "Files available in INCOMING folder : "
ls -ltr ./$INCOMING

printf "\n"

# check if files exists

# fail the job, if no files were downloaded

INCOMING_OUTPUT=$(ls -ltr ./$INCOMING)
if [[$INCOMING_OUTPUT = "total 0"]]; then

# To FAIL job - pipe message to STDERR "&2" and exit script

  echo "no files in directory">&2;
  exit 1;
fi

printf "\n"

# UPLOAD Workflow files to CFT

echo "=================================================="
echo "#### Upload file to CFT ####"

# if Sender Zone is INTERNET - replace "S3_BUCKET_INCOMING__IZ" to -> "S3_BUCKET_INCOMING__EZ"

if [ -n "${S3_BUCKET_INCOMING__IZ}" ]; then
    aws s3 sync ./$INCOMING "s3://${S3_BUCKET_INCOMING__IZ}/workflows/${WORKFLOW_ID}/files"
fi
echo "=================================================="

printf "\n"

echo "=================================================="
echo "SFTP script execution completed"
echo "=================================================="

Copy to clipboard
ErrorCopied
SFTP Scheduler as Receiver
This is a sample template for when you have an SFTP Server configured as a Receiver in your workflow.

# Updated: 16/08/24

#!/bin/bash
echo "=================================================="
echo "#### SFTP script execution started ####"
echo "=================================================="

printf "\n"

# env variables

echo "=================================================="
echo "#### Print env variables ####"
echo "SFTP_SERVER_HOSTNAME" ${SFTP_SERVER_HOSTNAME}
echo "SFTP_SERVER_USERNAME" ${SFTP_SERVER_USERNAME}
echo "SFTP_SERVER_AUTH_METHOD" ${SFTP_SERVER_AUTH_METHOD}
echo "SFTP_SERVER_PORT" ${SFTP_SERVER_PORT}
echo "WORKFLOW_ID" ${WORKFLOW_ID}
echo "=================================================="

printf "\n"

# Create OUTGOING folder

echo "=================================================="
echo "#### Creating Temp Folder ####"
export OUTGOING="OUTGOING_`date +%Y%m%d`"
mkdir $OUTGOING
echo "=================================================="

printf "\n"

# SFTP config

export PROXY="ProxyCommand nc -X connect -x cft2-prd-sftp-iz-proxy-nlb-c56328f1649d5d1b.elb.ap-southeast-1.amazonaws.com:3128 %h %p"
export HOST_KEY_ALGORITHM="-oHostKeyAlgorithms=+ssh-rsa"
export HOST_KEY_CHECK="-oStrictHostKeyChecking=no"
export PUB_KEY_ACCEPTED_KEY_TYPES="-o PubkeyAcceptedKeyTypes=+ssh-rsa"
export IDENTITY_FILE="-oIdentityFile=./id_rsa"

# DOWNLOAD Workflow files from CFT

echo "=================================================="
echo "#### Download Workflow files from CFT ####"

# if Receiver Zone is INTERNET - replace "S3_BUCKET_CLEAN__IZ" to -> "S3_BUCKET_CLEAN__EZ"

if [ -n "${S3_BUCKET_CLEAN__IZ}" ]; then
    aws s3 sync "s3://${S3_BUCKET_CLEAN__IZ}/workflows/${WORKFLOW_ID}/files" ./$OUTGOING
fi
echo "=================================================="

printf "\n"

echo "Files available in OUTGOING folder : "
ls -ltr ./$OUTGOING

printf "\n"

# check if files exists

# fail the job, if no files were downloaded

OUTGOING_OUTPUT=$(ls -ltr ./$OUTGOING)

if [[$OUTGOING_OUTPUT = "total 0"]]; then

# To FAIL job - pipe message to STDERR "&2" and exit script

  echo "no files in directory">&2;
  exit;
fi

printf "\n"

# PUSH files to Agency/Partner SFTP server

echo "=================================================="
echo "#### Connect to SFTP Server and push files ####"

# if auth method is "SSH Key AND Password"

# add "sshpass -e SFTP_SERVER_USER_PASSWORD" BEFORE "sftp ..." command

# e.g., "sshpass -e SFTP_SERVER_USER_PASSWORD sftp $ $ $ ..."

# if Receiver Zone is INTERNET, uncomment below:

# sftp  $ $ $ $ ${SFTP_SERVER_USERNAME}@$ <<EOF

sftp ${HOST_KEY_ALGORITHM} ${HOST_KEY_CHECK} ${PUB_KEY_ACCEPTED_KEY_TYPES} ${IDENTITY_FILE} -o "${PROXY}" ${SFTP_SERVER_USERNAME}@${SFTP_SERVER_HOSTNAME} <<EOF
ls -l
lcd ./$OUTGOING
put *
exit
EOF
echo "=================================================="

printf "\n"

echo "=================================================="
echo "SFTP script execution completed"
echo "=================================================="

Copy to clipboard
ErrorCopied
Other requirements
Custom environment variables
If any custom variable is added, please specify in this portion of the script.

For example, a Vanity ID variable is added below.

# Environment variables

echo "=================================================="
echo "#### Print env variables ####"
echo "SFTP_SERVER_HOSTNAME" ${SFTP_SERVER_HOSTNAME}
echo "SFTP_SERVER_USERNAME" ${SFTP_SERVER_USERNAME}
echo "SFTP_SERVER_AUTH_METHOD" ${SFTP_SERVER_AUTH_METHOD}
echo "SFTP_SERVER_PORT" ${SFTP_SERVER_PORT}
echo "WORKFLOW_ID" ${WORKFLOW_ID}
echo "VANITY_ID" ${VANITY_ID}
echo "=================================================="

Copy to clipboard
ErrorCopied
Vanity ID
If you have configured a Vanity ID in your workflow, replace the ${WORKFLOW_ID} variable with the ${VANITY_ID} variable. Ensure that you have already added ${VANITY_ID} as a new environment variable.

For example:

if [ -n "${S3_BUCKET_CLEAN__IZ}" ]; then
    aws s3 sync "s3://${S3_BUCKET_CLEAN__IZ}/workflows/${VANITY_ID}/files" ./$OUTGOING
fi

Copy to clipboard
ErrorCopied
Custom Port
If you have configured a Custom Port, add -P ${PortNumber} to the SFTP command. Ensure that you have already added ${PortNumber} as a new environment variable.

For example:

sftp ${HOST_KEY_ALGORITHM} ${HOST_KEY_CHECK} ${PUB_KEY_ACCEPTED_KEY_TYPES} ${IDENTITY_FILE} -o "${PROXY}" -P ${PortNumber} ${SFTP_SERVER_USERNAME}@${SFTP_SERVER_HOSTNAME} <<EOF
