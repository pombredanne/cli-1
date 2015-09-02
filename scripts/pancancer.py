#! /usr/bin/python3
import psutil
import json
import configparser
import time
import sys
import os
import subprocess
import logging
import cliff.app
import cliff.commandmanager
import cliff.command
import process_config
import urllib.request
import shutil

class WorkflowLister:
    "Get a listing of workflows from a source of workflow metadata."
    # Eventually, this data structure should come from some sort of online registry. For now, just define it in code.
    _workflows= {   'HelloWorld':
                    {
                        'full_name':'Workflow_Bundle_HelloWorld_1.0-SNAPSHOT_SeqWare_1.1.1',
                        'http_workflow':
                        {
                            'url':'https://s3.amazonaws.com/oicr.workflow.bundles/released-bundles/Workflow_Bundle_HelloWorld_1.0-SNAPSHOT_SeqWare_1.1.1.zip',
                            'version':'1.0-SNAPSHOT'
                        },
                        'containers':
                        {
                            'seqware_whitestar_pancancer': {
                                'name':'seqware_whitestar_pancancer',
                                'image_name': 'pancancer/seqware_whitestar_pancancer:1.1.1'
                            }
                        },
                        'ami_id':'ami-270cc34c',
                        'default-ini':'http://something.ini',
                        'instance-type':'m1.xlarge',
                        'lvm_devices':'/dev/xvdb,/dev/xvdc,/dev/xvdd,/dev/xvde'
                    },
                    'Sanger':
                    {
                        'full_name':'Workflow_Bundle_SangerPancancerCgpCnIndelSnvStr_1.0.8_SeqWare_1.1.0',
                        'http_workflow':
                        {
                            'url':'https://s3.amazonaws.com/oicr.workflow.bundles/released-bundles/Workflow_Bundle_SangerPancancerCgpCnIndelSnvStr_1.0.8_SeqWare_1.1.0.zip',
                            'version':'1.0.8'
                        },
                        'containers':
                        {
                            'seqware_whitestar_pancancer': {
                                'name':'seqware_whitestar_pancancer',
                                'image_name': 'pancancer/seqware_whitestar_pancancer:1.1.1'
                            }
                        },
                        'ami_id':'ami-270cc34c',
                        'default-ini':'https://raw.githubusercontent.com/ICGC-TCGA-PanCancer/SeqWare-CGP-SomaticCore/1.0.8/workflow/config/CgpCnIndelSnvStrWorkflow.ini',
                        'instance-type':'m1.xlarge',
                        'lvm_devices':'/dev/xvdb,/dev/xvdc,/dev/xvdd,/dev/xvde'
                    },
                    'BWA':
                    {
                        'full_name':'Workflow_Bundle_BWA_2.6.5_SeqWare_1.1.1',
                        'http_workflow':
                        {
                            'url':'https://s3.amazonaws.com/oicr.workflow.bundles/released-bundles/Workflow_Bundle_BWA_2.6.5_SeqWare_1.1.1.zip',
                            'version':'2.6.5'
                        },
                        'containers':
                        {
                            'seqware_whitestar_pancancer': {
                                'name':'seqware_whitestar_pancancer',
                                'image_name': 'pancancer/seqware_whitestar_pancancer:1.1.1'
                            }
                        },
                        'ami_id':'ami-270cc34c',
                        'default-ini':'https://raw.githubusercontent.com/ICGC-TCGA-PanCancer/Seqware-BWA-Workflow/2.6.5/workflow/config/workflow.ini',
                        'instance-type':'m1.xlarge',
                        'lvm_devices':'/dev/xvdb,/dev/xvdc,/dev/xvdd,/dev/xvde'
                    },
                    'DKFZ_EMBL':
                    {
                        'full_name':'Workflow_Bundle_DEWrapperWorkflow_1.0.5_SeqWare_1.1.1',
                        'http_workflow':
                        {
                            'url':'https://s3.amazonaws.com/oicr.workflow.bundles/released-bundles/Workflow_Bundle_DEWrapperWorkflow_1.0.5_SeqWare_1.1.1.zip',

                            'version':'1.0.5'
                        },
                        'containers':
                        {
                            'pcawg-delly-workflow': {
                                'name':'pcawg-delly-workflow',
                                'image_name': 'pancancer/pcawg-delly-workflow:1.0'
                            },
                            'seqware_whitestar_pancancer': {
                                'name':'seqware_whitestar_pancancer',
                                'image_name': 'pancancer/seqware_whitestar_pancancer:1.1.1'
                            },
                            'pancancer_upload_download': {
                                'name':'pancancer_upload_download',
                                'image_name':'pancancer/pancancer_upload_download:1.2'
                            }
                        },
                        's3_containers':
                        {
                            'dkfz_dockered_workflows':
                            {
                                'name':'dkfz_dockered_workflows',
                                'url':'s3://oicr.docker.private.images/dkfz_dockered_workflows_1.3.tar'
                            }
                        },
                        'ami_id':'ami-270cc34c',
                        'default-ini':'https://raw.githubusercontent.com/ICGC-TCGA-PanCancer/DEWrapperWorkflow/1.0.6/workflow/config/DEWrapperWorkflow.ini',
                        'instance-type':'m1.xlarge',
                        'lvm_devices':'/dev/xvdb,/dev/xvdc,/dev/xvdd,/dev/xvde'
                    }
                }

    @staticmethod
    def get_workflow_names():
        keys = ''
        for k in WorkflowLister._workflows:
            keys += k+'\n'
        return keys

    @staticmethod
    def get_workflow_details(workflow_name):
        return WorkflowLister._workflows[workflow_name]

###

class Workflows(cliff.command.Command):
    "This command  can help you configure and select workflows."
    log = logging.getLogger(__name__)

    def get_parser(self,prog_name):
        parser = super(Workflows,self).get_parser(prog_name)
        #parser.add_mutually_exclusive_group()
        workflows_subparser = parser.add_subparsers(title='subcommands',help='workflows subcommands: list and config',dest='subparser_name')
        workflows_subparser.add_parser('list',help='Get a list of workflows')
        workflows_subparser.add_parser('config',help='Generate a default config file for a specific workflow').add_argument('--workflow', dest='workflow_name',help='Name of workflow to configure')
        return parser

    def take_action(self, parsed_args):
        subparser_name=vars(parsed_args)['subparser_name']
        self.log.debug('subparser: %s',subparser_name)
        if subparser_name=='list':
            workflow_list = WorkflowLister.get_workflow_names()
            self.log.info ('Available workflows are:')
            self.log.info(workflow_list)

        elif subparser_name=='config':
            workflow_name=vars(parsed_args)['workflow_name']
            if workflow_name in WorkflowLister.get_workflow_names():
                ini_file_path = os.path.expanduser('~/ini-dir/'+workflow_name+'.ini')
                if workflow_name != 'HelloWorld':
                    workflow_details = WorkflowLister.get_workflow_details(workflow_name)
                    url = workflow_details['default-ini']

                    with urllib.request.urlopen(url) as response, open(ini_file_path,'wb') as ini_file:
                        shutil.copyfileobj(response,ini_file)
                else:
                    with open(ini_file_path,'w') as ini_file:
                        ini_file.write('greeting=Greetings_from_Panancer_CLI')

                self.log.info('generating default INI in /home/ubuntu/ini-dir/'+workflow_name+'.ini for workflow '+workflow_name)
            else:
                self.log.info ('Sorry, but '+workflow_name+' is not a valid workflow name. Please use the command \'workflows list\' to see a list of available workflows.')
        else:
            self.log.info ('The available subcommands are \'list\' and \'config\'.')

###

class SysConfig(cliff.command.Command):
    "This command will setup the pancancer system configuration."
    log = logging.getLogger(__name__)

    def get_parser(self,prog_name):
        parser = super(SysConfig,self).get_parser(prog_name)
        sysconf_subparser = parser.add_argument('--config',dest='config_path',help='The path to your pancancer config file, if it already exists.',required=False)
        return parser

    def _get_config_value(self,user_value,prev_user_value,message, alt_condition=None):
        "This function will prompt the use with a question and will keep prompting them until a valid value is given."
        while (alt_condition == None and user_value.strip() == '') or (alt_condition != None and alt_condition(user_value)):
            prev_value_prompt = ''
            if prev_user_value != '':
                prev_value_prompt = '[Press \"ENTER\" to use the previous value: '+prev_user_value+', or type a new value if you want]'
            user_value = input(message + ' ' + prev_value_prompt+'? ')
            user_value = user_value.strip() or prev_user_value.strip()
            if user_value=='':
                self.log.info('This value cannot be blank.')

        return user_value

    def take_action(self, parsed_args):
        self.log.info('Setting up pancancer config files.')
        config_path=vars(parsed_args)['config_path']

        if config_path != None:
            # if the user specifies a path to an existing file, they can use that instead of the interactive process.
            self.log.debug('path to config file: ' + config_path)
            process_config.main(config_path)
        else:
            # if the user did not specify a config, ask them questions and then WRITE/update a config!
            pancancer_config_path=os.path.expanduser('~/.pancancer/simple_pancancer_config.json')
            config_data={}
            if os.path.isfile(pancancer_config_path):
                #Read the pancancer_config.json file if it exists
                with open(pancancer_config_path,'r') as pancancer_config_file:
                    config_data = json.load(pancancer_config_file)

            pancancer_config={}
            prev_fleet_size = ''
            if 'max_fleet_size' in config_data:
                prev_fleet_size = config_data['max_fleet_size']
            fleet_size=''
            fleet_size = self._get_config_value(fleet_size, prev_fleet_size, 'How many VMs do you want in your fleet', alt_condition = lambda x: x.strip()=='' or x.isdigit() == False or int(x)<=0 )


            prev_security_group = ''
            security_group = ''
            if 'security_group' in config_data:
                prev_security_group = config_data['security_group']
            if prev_security_group.strip() == '':
                prev_security_group = 'default'
            security_group = self._get_config_value(security_group, prev_security_group,'What AWS Security Group should the VMs belong to')

            aws_config_path = os.path.expanduser('~/.aws/config')
            aws_key=''
            aws_secret_key=''
            prev_aws_key=''
            prev_aws_secret_key=''
            if os.path.isfile(aws_config_path):
                # read the file, get the values
                aws_config = configparser.ConfigParser()
                aws_config.read(aws_config_path)
                prev_aws_key = aws_config['default']['aws_access_key_id']
                prev_aws_secret_key = aws_config['default']['aws_secret_access_key']

            # AWS Key and Secret Key should only be asked for if for some reason they are NOT available (they *should* be, but stuff happens...)
            if prev_aws_key.strip() == '' or prev_aws_secret_key.strip() == '':
                aws_key = self._get_config_value(aws_key,prev_aws_key,'What is your AWS Key')
                aws_secret_key = self._get_config_value(aws_secret_key,prev_aws_secret_key,'What is your AWS Secret Key')
                # If the AWS keys weren't available, ~/.aws/config is either not present or missing values, so re-write it.
                aws_config = configparser.ConfigParser()
                aws_config['default'] = {'aws_access_key_id':aws_key, 'aws_secret_access_key':aws_secret_key}
                with open(aws_config_path,'w') as aws_configfile:
                    aws_config.write(aws_configfile,space_around_delimiters=False)
            else:
                aws_key = prev_aws_key
                aws_secret_key = prev_aws_secret_key

            # also: get fleet name, PEM key path, and key name from env. If everything went smoothly, these values should be in
            # /opt/from_host/config/pancancer.config
            # Actually, fleet name should be coming from process_config.py, not here, since it's passed into the container as an environment variable.
            # If it's NOT there, we should askt he user for these values.
            bootstrap_config_path='/opt/from_host/config/pancancer.config'
            pem_key_path=''
            prev_pem_key_path=''
            key_name=''
            prev_key_name=''
            if os.path.isfile(bootstrap_config_path):
                self.log.debug('bootstrap config file exists at: '+bootstrap_config_path)
                # load simple config file (it should have been generated by install_bootrap) and get values.
                H = dict(line.strip().split('=') for line in open(bootstrap_config_path))
                if 'PEM_PATH' in H:
                    prev_pem_key_path = H['PEM_PATH']
                if 'KEY_NAME' in H:
                    prev_key_name = H['KEY_NAME']

                if prev_pem_key_path.strip() != '':
                    pem_key_path = prev_pem_key_path
                if prev_key_name.strip() != '':
                    key_name = prev_key_name
            else:
                self.log.debug('bootstrap config file cannot be found at: '+bootstrap_config_path+' so a new one will be written.')

            # Only ask the use about these if one or the other does not exist (indicates there might be a config value/file problem somewhere)
            if prev_pem_key_path.strip()=='' or prev_key_name.strip()=='':
                pem_key_path = self._get_config_value(pem_key_path, prev_pem_key_path, 'What is the path to the AWS pem key file that your new VMs to use')
                key_name = self._get_config_value(key_name, prev_key_name, 'What is the Name of this key in AWS')
                #Now write the bootstrap config file, but only if we had to ask the user for help filling in the details.
                with open(bootstrap_config_path,'w') as bootstrap_config:
                    bootstrap_config.write('PEM_PATH='+pem_key_path+'\n')
                    bootstrap_config.write('KEY_NAME='+key_name+'\n')
                    bootstrap_config.write('FLEET_NAME='+os.environ['FLEET_NAME']+'\n')

            # Now, write the simple JSON config that will be used for the rest of pancancer system.
            pancancer_config = { 'max_fleet_size':fleet_size, 'path_to_key': pem_key_path,
                                'name_of_key':key_name, 'aws_secret_key':aws_secret_key,
                                'security_group': security_group, 'aws_key':aws_key }

            if not os.path.exists(os.path.expanduser('~/.pancancer')):
                os.makedirs(os.path.expanduser('~/.pancancer'))

            with open(pancancer_config_path,'w') as simple_pancancer_config:
                simple_pancancer_config.write(str(json.dumps(pancancer_config,sort_keys=True, indent=4) ))
                self.log.info('Your new pancancer system config file has been written to '+pancancer_config_path)
                self.log.info('The next time you want to run \"pancancer sysconfig\", you can use this file like this: ')
                self.log.info('pancancer sysconfig --config '+pancancer_config_path)

            # Now that a config is written, USE IT!!
            process_config.main(pancancer_config_path)


###

class DaemonCommand(cliff.command.Command):
    "Parent class for commands that start/stop daemons"
    service_name=''
    log = logging.getLogger(__name__)

    def _do_start(self,start_cmd):
        "Start a process, using flock to ensure that it can't be started multiple times."
        self.log.debug (start_cmd)
        pid_file_path='/tmp/arch3_'+self.service_name+'.pid'
        # set start_new_session=True so that we can kill flock and all it's child processes by killing the process group whose pgid is the same as the flock pid.
        # We don't want to use subprocess.call() or check_call() here because those will wait for the command to complete. Since the child process will run in "endless" mode,
        # we really don't want *this* script to run endlessly - we want to start the child and let it keep running in the background.
        p = subprocess.Popen(start_cmd.split(' '),start_new_session=True)
        # Wait a moment... if we get ANY response, it means that the process did not start, probably because it's already been started.
        time.sleep(2)
        p.poll()

        if p.returncode==1:
            self.log.info('The '+self.service_name+' process might already be running.')
        else:
            self.log.debug('pid: '+str(p.pid))
            self.log.info('The service has been started, check the log files for more detail.')
            # ONLY if the service was started new (and not already running) write a pid file so we will know which processes to kill later.
            with open(pid_file_path,'w') as pidfile:
                pidfile.write(str(p.pid))


    def _do_stop(self,stop_cmd):
        "Stop a process."
        pid = ''
        # Read the pid from the file.
        pid_file_path='/tmp/arch3_'+self.service_name+'.pid'
        if os.path.isfile(pid_file_path):
            with open(pid_file_path,'r') as pidfile:
                pid = pidfile.readline()

            stop_cmd += pid
            self.log.debug (stop_cmd)

            self.log.debug('pid: '+pid)

            if psutil.pid_exists(int(pid)):
                returncode = subprocess.call(stop_cmd.split(' '))
                if returncode == 0:
                    self.log.info ('The '+self.service_name+' process has been stopped.')
                    os.remove(pid_file_path)
            else:
                self.log.info('The '+self.service_name+' process with PID '+pid+' does not appear to be running.')
        else:
            self.log.info('The '+self.service_name+' process does not appear to be running.')

    def get_parser(self,prog_name):
        parser = super(DaemonCommand,self).get_parser(prog_name)
        subparser = parser.add_subparsers(title='subcommands',help='coordinator subcommands: start, stop, restart',dest='service_state')
        subparser.required=True
        subparser.add_parser('start',help='Start the '+self.service_name+' service')
        subparser.add_parser('stop',help='Stop the '+self.service_name+' service')
        subparser.add_parser('restart',help='Stop and then start the '+self.service_name+' service')
        return parser

    def take_action(self, parsed_args):
        subparser_name=vars(parsed_args)['service_state']
        self.log.debug('working on service: '+self.service_name)
        self.log.debug('subparser: %s',subparser_name)
        # Use flock to ensure that multiple instances of the "service" cannot run at the same time.
        start_cmd='flock -n /tmp/arch3_'+self.service_name+'.lock ' +self.service_name+' --config /home/ubuntu/arch3/config/masterConfig.ini --endless'
        # Negate the PID of the process to kill the process group.
        stop_cmd='kill -KILL -'
        if subparser_name=='start':
            self._do_start(start_cmd)
        elif subparser_name=='stop':
            self._do_stop(stop_cmd)
        elif subparser_name=='restart':
            self._do_stop(stop_cmd)
            self._do_start(start_cmd)

###

class Coordinator(DaemonCommand):
    "The Coordinator will process existing job orders into requests for VMs and jobs that will be picked up by running VMs."
    log = logging.getLogger(__name__)
    def __init__(self,Coordinator,args):
        self.service_name='Coordinator'

###

class Provisioner(DaemonCommand):
    "The Provisioner will launcher worker VMs as needed based on the workflow orders sent to the system."
    log = logging.getLogger(__name__)
    def __init__(self,Provisioner,args):
        self.service_name='Provisioner'

###

class Generator(cliff.command.Command):
    "This Generator will generate new job orders."
    log = logging.getLogger(__name__)
    def get_parser(self,prog_name):
       parser = super(Generator,self).get_parser(prog_name)
       parser.add_argument('--workflow',dest='workflow_name',help='The name of the workflow for which you would like to generate jobs.',required=True)
       return parser

    def take_action(self, parsed_args):
        workflow_name=vars(parsed_args)['workflow_name']
        self.log.debug('workflow_name: %s',workflow_name)
        if not (workflow_name in WorkflowLister.get_workflow_names()):
            self.log.info('Oh, I\'m SO sorry, but '+workflow_name+' is not the name of an available workflow.\nPlease use the command \'workflows list\' to see the list of currently available workflows.')
        else:
            workflow_details = WorkflowLister.get_workflow_details(workflow_name)
            generator_cmd = 'Generator --workflow-name '+workflow_name+' --workflow-version '+workflow_details['http_workflow']['version']+' --workflow-path '+'/workflows/'+workflow_details['full_name']+' --ini-dir '+'/home/ubuntu/ini-dir --config /home/ubuntu/arch3/config/masterConfig.ini'
            self.log.debug(generator_cmd)
            # Before generating the job, we have to update params.json with the workflow/container info about the requested workflow.
            paramsData=''
            with open('/home/ubuntu/params.json','r') as params_file:
                paramsData = json.load(params_file)
                if 'http_workflow' in workflow_details:
                    paramsData['http_workflows'] = {}
                    paramsData['http_workflows'][workflow_name] = workflow_details['http_workflow']
                    paramsData['http_workflows'][workflow_name]['name'] = workflow_details['full_name']
                if 's3_workflows' in workflow_details:
                    paramsData['s3_workflows'] = {}
                    paramsData['s3_workflows'][workflow_name] = workflow_details['s3_workflows']
                    paramsData['s3_workflows'][workflow_name]['name'] = workflow_details['full_name']
                if 'containers' in workflow_details:
                    paramsData['containers'] = workflow_details['containers']
                if 's3_containers' in workflow_details:
                    paramsData['s3_containers'] = workflow_details['s3_containers']
                if 'http_containers' in workflow_details:
                    paramsData['http_containers'] = workflow_details['http_containers']

                paramsData['lvm_device_whitelist'] = workflow_details['lvm_devices']
                paramsData['workflow_name'] = workflow_name

            # Now write the params.json file.
            with open('/home/ubuntu/params.json','w+') as params_file:
                params_file.write(str(json.dumps(paramsData,sort_keys=True, indent=4) ))

            # Update the youxia config file with the correct AMI and instance-type
            config = configparser.ConfigParser()
            config.read('/home/ubuntu/.youxia/config')
            config['deployer']['instance_type']=workflow_details['instance-type']
            config['deployer']['ami_image']=workflow_details['ami_id']
            with open('/home/ubuntu/.youxia/config','w') as youxia_configfile:
                config.write(youxia_configfile,space_around_delimiters=True)

            subprocess.call(generator_cmd.split(' '))

###

class Reports(cliff.command.Command):
    "This will generate reports on the command line."
    log = logging.getLogger(__name__)
    def get_parser(self,prog_name):
        parser = super(Reports,self).get_parser(prog_name)
        subparser = parser.add_subparsers(title='subcommands',help='reporting subcommands: gather, info, jobs, provisioned, status, help',dest='report_subcmd')
        subparser.required=True
        subparser.add_parser('gather',help='gathers the last message sent by each worker and displays the last line of it')
        subparser.add_parser('info',help='retrieves detailed information on provisioned instances')
        subparser.add_parser('jobs',help='retrieves detailed information on jobs')
        subparser.add_parser('provisioned',help='retrieves detailed information on provisioned instances')
        subparser.add_parser('status',help='retrieves configuration and version information on arch3')
        subparser.add_parser('youxia',help='ask youxia for all information on instances known to the cloud APIs that are configured')
        subparser.add_parser('help',help='Prints a help message for the reporting system.')
        return parser

    def take_action(self, parsed_args):
        subcmd = vars(parsed_args)['report_subcmd']
        cmd_str='java -cp reporting.jar info.pancancer.arch3.reportcli.ReportCLI --config /home/ubuntu/arch3/config/masterConfig.ini'
        if subcmd!='help':
            # If you don't pass a reporting subcommand to ReportCLI, it will print the help text by default.
            cmd_str='java -cp reporting.jar info.pancancer.arch3.reportcli.ReportCLI --config /home/ubuntu/arch3/config/masterConfig.ini '+subcmd

        subprocess.call(cmd_str.split(' '))

###

class Status(cliff.command.Command):
    "This will return status information about the launcher."
    log = logging.getLogger(__name__)

    def _do_sql_status(self, sql):
        "Executes a command against the postgres database"
        cmd = 'psql -U queue_user queue_status -c'
        self.log.debug(cmd)
        sql_cmd = cmd.split(' ')
        sql_cmd.append(sql)
        self.log.debug(sql_cmd)
        subprocess.call(sql_cmd)

    def _check_service_with_name(self, service_name):
        "Uses pgrep to check if a process matches the pattern 'java.*<service_name>'"
        # Use pgrep to check if the java process is running.
        cmd = 'pgrep -fla java.*'+service_name
        output=''
        try:
            output = subprocess.check_output(cmd.split(' '),universal_newlines=True)
        except subprocess.CalledProcessError as e:
            # If pgrep returns nothing, then the process is not running.
            self.log.info ('The '+service_name+' process does not appear to be running.')

        if output!='':
            # Print the message with the PID
            self.log.info ('The '+service_name+' appears to be running with PID: '+(output.split(' '))[0])

    def _do_service_checks(self):
        "Check the Coordinator and Provisioner."
        self._check_service_with_name('Coordinator')
        self._check_service_with_name('Provisioner')

    def get_parser(self,prog_name):
        parser = super(Status,self).get_parser(prog_name)
        subparser = parser.add_subparsers(title='subcommands',help='status subcommands: queues, jobs, job_status',dest='status_subcmd')
        subparser.required=True
        subparser.add_parser('queues',help='Prints some basic status information on the RabbitMQ message queues.')
        subparser.add_parser('job_status',help='Prints counts of jobs by status.')
        subparser.add_parser('jobs',help='Prints data from the job table (omits standard error and standard out).')
        subparser.add_parser('services',help='Prints the status of the coordinator and provisioner')
        return parser

    def take_action(self,parsed_args):
        subcmd = vars(parsed_args)['status_subcmd']
        cmd=''
        sql=''
        if subcmd == 'queues':
            #QueueStatus is a simple wrapper script around rabbitmq stats, as a part of architecture-setup
            cmd = '/bin/bash QueueStats'
            subprocess.call(cmd.split(' '))
        elif subcmd == 'job_status':
            #cmd = ('psql -U queue_user queue_status -c '.split(' ')).append('"select count(*), status from job group by status;"')
            sql='select count(*), status from job group by status;'
            self._do_sql_status(sql)
        elif subcmd == 'jobs':
            sql='select status, job_id, job_uuid, workflow, create_timestamp, update_timestamp from job;'
            self._do_sql_status(sql)
        elif subcmd == 'services':
            self._do_service_checks()

###

class PancancerApp(cliff.app.App):
    log = logging.getLogger(__name__)

    def __init__(self):
        commandMgr = cliff.commandmanager.CommandManager('pancancer.app')
        super(PancancerApp, self).__init__(
            description='Pancancer CLI',
            version='1.0',
            command_manager=commandMgr,
        )
        commands = {
            'workflows': Workflows,
            'generator': Generator,
            'reports': Reports,
            'provisioner': Provisioner,
            'coordinator': Coordinator,
            'status': Status,
            'sysconfig': SysConfig
        }
        for k, v in commands.items():
            commandMgr.add_command(k, v)


    def initialize_app(self, argv):
        self.log.debug('initialize_app')

    def prepare_to_run_command(self, cmd):
        self.log.debug('prepare_to_run_command %s', cmd.__class__.__name__)

    def clean_up(self, cmd, result, err):
        self.log.debug('clean_up %s', cmd.__class__.__name__)
        if err:
            self.log.debug('got an error: %s', err)


def main(argv=sys.argv[1:]):
    app = PancancerApp()
    return app.run(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))