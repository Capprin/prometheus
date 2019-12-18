import click, boto3

def start_instance(ami, type, keypair):
    pass

def terminate_instance(id):
    pass

@click.command()
@click.option("-t", "--type", default="tmp", help="instance type")
@click.argument("directory")
def init (type, directory):
    click.echo("Creating an instance of type " + type + ", starting program in directory " + directory)

if __name__ == '__main__':
    init()