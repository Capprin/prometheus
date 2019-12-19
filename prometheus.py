import sys, os, click, math, boto3

# workflow:
#    create instances. Need:
#        - ami (option, with default)
#        - type (option, with default. Also provide a reference)
#        - keypair (generated for each instance, stored in local file)
#       will produce ec2 instance we can access. We store necessary information in a file in provided directory
#    push program to instances
#    wait for program to end
#       include interrupted behavior (close instance?)
#    download program data
#    terminate instance

# computes directory size, in bytes. Probably shouldn't be used.
def get_size(start_path = '.'):
    total_size = 0
    for path, dirs, files in os.walk(start_path):
        for f in files:
            fp = os.path.join(path, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

# click definitions
@click.group()
def cli():
    """Creates EC2 instances to run programs in the cloud."""
    pass

#TODO: Make these options choices (how should I do this so they're not super insane?)
@cli.command()
@click.option('-k', '--keypair', required=True, help='ssh key used to access instance')
@click.option('-s', '--size', type=click.INT, help = 'EBS size, in GB. Highly Recommended!')
@click.option('-t', '--type', default='t2.micro', help='instance type')
@click.option('-a', '--ami', default='ami-08d489468314a58df', help='amazon machine image')
@click.option('-p', '--persist', help='keep instance running', flag_value=True)
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
def run (directory, keypair, size, ami, type, persist):
    """Creates and runs an AWS EC2 instance that runs the process stored in DIRECTORY."""

    ec2_resource = boto3.resource('ec2', region_name = 'us-west-2')
    ec2_client = boto3.client('ec2')

    # estimate storage size at the directory space (better to provide size)
    # set size to 8 (minimum) if we're less than that
    if size is None:
        size = math.ceil(get_size(directory)/1000000000)
        click.echo('Instance size not provided, making my best guess...')
    if size < 8:
            size = 8

    instance_list = None
    block_device_mappings = [
        {
            'DeviceName': '/dev/xvda',
            'Ebs' : { 
                'VolumeSize' : size 
            }
        }
    ]

    # create ec2 instance
    try:
        instance_list = ec2_resource.create_instances(BlockDeviceMappings=block_device_mappings, ImageId=ami, InstanceType=type, KeyName=keypair, MinCount=1, MaxCount=1)
    except:
        #TODO: Better error logging
        click.echo('Failed to create ec2 instance.')
        exit(1)
    else:
        click.echo('Created ec2 instance with id ' + instance_list[0].id)

    #TODO: Save instance information if:
    #   - persisting
    #   - "save" flag is set

    #TODO: Move directory contents into instance

    #TODO: Start main process
    #   - wait until exit (normally):
    #       - if success, continue normally
    #       - if failure, prompt for persistence (for debug)
    #   - don't wait (optional parameter, maybe)

    #TODO: Move directory contents from instance
    #   - only if done with the instance

    # terminate ec2 instance if we're supposed to
    instance_ids = [instance.id for instance in instance_list]
    if not persist:
        try:
            ec2_client.terminate_instances(InstanceIds = instance_ids)
        except:
            #TODO: Handle this better. Maybe wait?
            click.echo('Failed to terminate ec2 instance')
            exit(1)
        else:
            click.echo('Terminated instance successfully.')
    else:
        click.echo('Persisting ec2 instance.')

    click.echo('Done.')

@cli.group()
def reference():
    """Concise reference for optional provided parameters. More information will always be available at aws.amazon.com/ec2/"""
    pass

@reference.command()
def type():
    """
    Reflects focus of hardware being used by each instance. In general:
    \b
    General Purpose: Use T3, M5
    Compute Focused: Use C5
    Memory Focused: Use R5
    More Specialized: See official documentation.

    Each type is sized: nano, micro, small, medium, large, xlarge, metal, etc.
    The size corresponds to machine capability of the instance.
    \b
    Examples:
    t2.micro (default for this platform)
    m5.large
    c5.xlarge
    r5.metal

    Official documentation available at https://aws.amazon.com/ec2/instance-types/.
    """
    pass

@reference.command()
def ami():
    """
    \b
    Starting image for instance. Some example default available AMI's:
    Amazon Linux: ami-08d489468314a58df (default for this platform)
    Red Hat: ami-087c2c50437d0b80d
    Ubuntu Server: ami-06d51e91cea0dac8d
    Windows Server: ami-0f3f4855746899521

    Specific AMI's are available for each use case, and should be explored in the aws console.
    """
    pass

#TODO: write stop command
#TODO: figure out reference
#   - instance types overview/reference?
#   - brief ami reference?


# start cli
if __name__ == '__main__':
    cli()