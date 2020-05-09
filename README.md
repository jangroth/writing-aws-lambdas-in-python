# An opinionated approach to writing AWS Lambdas in Python

Example code for TODO.

![Flow Diagram](media/example_flow.png)

## How to deploy

Assumes:
* Understanding of how to build and run AWS SAM applications
* AWS default profile configured or `AWS_PROFILE` set

Prerequisites:
* Python 3.7
* pip
* make
* aws-cli

Tested on:
* Linux
* MacOS 

### Install dependencies

```shell script
make create-artifact-bucket
```

### Create artifact bucket

Edit `ARTIFACT_BUCKET` in `Makefile` to become globally unique. E.g. `default-sg-remediation-artifacts-[your account id]` 

```shell script
make create-artifact-bucket
```

### Run tests and deploy

```shell script
make test
make deploy
```
