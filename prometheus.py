import sys, os, math, json, zipfile, click, boto3

# PROMETHEUS
# instance-manager: only for managing ec2 instances

# computes directory size, in bytes. Probably shouldn't be used.
def get_sub_items(start_path = '.'):
    sub_items = []
    for path, dirs, files in os.walk(start_path):
        for f in files:
            fp = os.path.join(path, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                sub_items.append(fp)

    return sub_items


# click definitions
@click.group()
def cli():
    """Creates EC2 instances to run programs in the cloud."""
    pass

#TODO: Make these options choices (how should I do this so they're not super insane?)
@cli.command()
@click.option('-k', '--key-name', 'keypair', required=True, help='amazon keypair used to access instance')
@click.option('-s', '--size', type=click.INT, help = 'EBS size, in GB. Highly Recommended!')
@click.option('-t', '--type', default='t2.micro', help='instance type')
@click.option('-a', '--ami', default='ami-08d489468314a58df', help='amazon machine image')
@click.option('-g', '--security-group-name', 'securitygroup', help='provided security group. MUST allow ssh from this machine.')
@click.argument('directory', type=click.Path(exists=True, file_okay=False, dir_okay=True), default='.')
def start (directory, keypair, size, ami, securitygroup, type):
    """Creates and runs an AWS EC2 instance that runs the process stored in DIRECTORY."""

    # create ec2 resource; main workhorse
    try:
        ec2_resource = boto3.resource('ec2', region_name = 'us-west-2')
    except:
        click.echo('Failed to create EC2 resource.')
        exit(1)

    # security group management
    group_id = None
    try:
        security_groups = ec2_resource.security_groups.all()
    except:
        click.echo('Failed to read existing security groups.')
        exit(1)
    # generate security group if we're missing one
    if securitygroup is None:
        click.echo('No security group provided.')
        # see if we've made one before
        for group in security_groups:
            if group.group_name == 'prometheus':
                group_id = group.group_id
                click.echo('Using existing prometheus security group')
                break
        # if we still don't have one, make one
        if group_id is None:
            click.echo('Creating security group for prometheus')
            try:
                group = ec2_resource.create_security_group(
                    GroupName='prometheus', 
                    Description='Security group created automatically for prometheus CLI'
                )
                ipv4 = click.prompt('Provide your external IPv4 address') + '/32'
                # allow ingresses we need
                group.authorize_ingress(CidrIp=ipv4, FromPort=22, ToPort=22, IpProtocol='tcp')
                group_id = group.group_id
            except:
                click.echo('Failed to create a new security group.')
                exit(1)
            else:
                click.echo('Successfully created prometheus security group')
    else:
        # finding provided security group
        for group in security_groups:
            if group.group_name == securitygroup:
                click.echo('Using provided security group: ' + securitygroup)
                group_id = group.group_id
                break
        # if we still don't have one, exit
        if group_id is None:
            click.echo('Provided security group ' + securitygroup + ' does not exist')
            exit(1)

    #TODO: Should we do the above for keys?

    # estimate storage size at the directory space (better to provide size)
    # set size to 8 (minimum) if we're less than that
    if size is None:
        files = get_sub_items(directory)
        total = 0
        for f in files:
            total += os.path.getsize(f)
        size = math.ceil(total/1000000000)
        click.echo('Instance size not provided, making my best guess...')
    if size < 8:
            size = 8
    click.echo('Using EBS volume size of %igb' % (size))

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
        instance_list = ec2_resource.create_instances(
            BlockDeviceMappings=block_device_mappings, 
            SecurityGroupIds=[group_id],
            ImageId=ami, 
            InstanceType=type, 
            KeyName=keypair, 
            MinCount=1, 
            MaxCount=1
        )
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

    # save instance information
    click.echo('Writing instance information to ' + directory + '/instance-info.json')
    instance_info = []
    for instance in instance_list:
        info = {
            'id' : instance.id,
            'ami' : instance.image_id,
            'type': instance.instance_type,
            'key-name' : instance.key_name,
            'public-dns' : instance.public_dns_name,
            'public-ip' : instance.public_ip_address
        }
        instance_info.append(info)
    out_file = open(directory + '/instance-info.json','w')
    out_file.write(json.dumps(instance_info))
    out_file.close()

    click.echo('Done.')

# restarts stopped ec2 instances
@cli.command()
@click.argument('instance_id', nargs=-1)
def restart(instance_id):
    """Restarts stopped instances with provided INSTANCE_ID's"""
    click.echo('Restarting instance(s)...')
    try:
        ec2 = boto3.client('ec2')
        ec2.start_instances(InstanceIds = list(instance_id))
    except:
        click.echo('Failed to restart instances.')
    else:
        click.echo('Start command sent to aws successfully.')
    click.echo('Done.')

# stops instances with provided ids
@cli.command()
@click.argument('instance_id', nargs=-1)
def stop (instance_id):
    """Stops running instances with provided INSTANCE_ID's"""
    click.echo('Stopping instance(s)...')
    try:
        ec2 = boto3.client('ec2')
        ec2.stop_instances(InstanceIds = list(instance_id))
    except:
        click.echo('Failed to stop instances.')
    else:
        click.echo('Stop command sent to aws successfully.')
    click.echo('Done.')

# terminates instances with provided ids
@cli.command()
@click.argument('instance_id', nargs=-1)
def terminate(instance_id):
    """Terminates running instances with provided INSTANCE_ID's."""
    click.echo('Terminating instance(s)...')
    try:
        ec2 = boto3.client('ec2')
        ec2.terminate_instances(InstanceIds = list(instance_id))
    except:
        click.echo('Failed to terminate instances.')
    else:
        click.echo('Terminate command sent to aws successfully.')
    click.echo('Done.')

# start cli
if __name__ == '__main__':
    cli()