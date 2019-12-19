import sys, os, math, json, click, boto3

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
@click.option('-r', '--save', help='save instance information after start', flag_value=True)
@click.option('-p', '--persist', help='keep instance running', flag_value=True)
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
def run (directory, keypair, size, ami, type, save, persist):
    """Creates and runs an AWS EC2 instance that runs the process stored in DIRECTORY."""

    try:
        ec2_resource = boto3.resource('ec2', region_name = 'us-west-2')
    except:
        click.echo('Failed to create EC2 resource.')
        exit(1)

    # estimate storage size at the directory space (better to provide size)
    # set size to 8 (minimum) if we're less than that
    if size is None:
        size = math.ceil(get_size(directory)/1000000000)
        click.echo('Instance size not provided, making my best guess...')
    if size < 8:
            size = 8
    click.echo('Using EBS volume size of %i' % (size))

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
        click.echo('Failed to create ec2 instance(s).')
        exit(1)
    else:
        click.echo('Created ec2 instance(s) with id(s) ', nl=False)
        for instance in instance_list:
            click.echo(instance.id + ' ', nl=False)
        click.echo('') #final newline

    # block until instances are running
    click.echo('Updating local instance information (this may take a while)')
    for instance in instance_list:
        instance.wait_until_running()
        instance.reload()

    # save instance information if required
    if save or persist:
        click.echo('Writing instance information to ' + directory + '/instance-info.json')
        instance_info = []
        for instance in instance_list:
            info = {
                'id' : instance.id,
                'ami' : instance.image_id,
                'type': instance.instance_type,
                'key-name' : instance.key_name,
                #'launch-time' : instance.launch_time,
                'public-dns' : instance.public_dns_name,
                'public-ip' : instance.public_ip_address
            }
            instance_info.append(info)
        out_file = open(directory + '/instance-info.json','w')
        out_file.write(json.dumps(instance_info))
        out_file.close()

    #TODO: Move directory contents into instance

    #TODO: Start main process
    #   - wait until exit (normally):
    #       - if success, continue normally
    #       - if failure, prompt for persistence (for debug)
    #   - don't wait (optional parameter, maybe)

    #TODO: Move directory contents from instance
    #   - only if done with the instance

    # terminate ec2 instance if we're supposed to
    if not persist:
        try:
            for instance in instance_list:
                instance.terminate()
        except:
            #TODO: Handle this better. Maybe wait?
            click.echo('Failed to terminate ec2 instance')
            exit(1)
        else:
            click.echo('Terminated instance successfully.')
    else:
        click.echo('Persisting ec2 instance.')

    click.echo('Done.')


# stops instances with provided ids
@cli.command()
@click.argument('instance_id', nargs=-1)
def stop(instance_id):
    """Stops running instances with provided INSTANCE_ID's."""
    click.echo('Terminating instance(s)...')
    try:
        ec2 = boto3.client('ec2')
        ec2.terminate_instances(InstanceIds = list(instance_id))
    except:
        click.echo('Failed to terminate instances.')
    click.echo('Done.')

#TODO: figure out reference
#   - instance types overview/reference?
#   - brief ami reference?


# start cli
if __name__ == '__main__':
    cli()