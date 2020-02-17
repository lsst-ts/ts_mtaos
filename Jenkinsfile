#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        // Use the label to assign the node to run the test.
        // It is recommended by SQUARE team do not add the label.
        docker {
            image 'lsstts/aos_aoclc:w_2020_06_sal'
            args "-u root --entrypoint=''"
        }
    }

    triggers {
        pollSCM('H * * * *')
    }

    environment {
        //SAL user home
        SAL_USERS_HOME="/home/saluser"
        // SAL setup file
        SAL_SETUP_FILE="/home/saluser/.setup.sh"
        // SAL-related repositories directory
        SAL_REPOS="/home/saluser/repos"
        // XML report path
        XML_REPORT="jenkinsReport/report.xml"
        // Module name used in the pytest coverage analysis
        MODULE_NAME="lsst.ts.MTAOS"
    }

    stages {
        stage ('Install Requirements') {
            steps {
                // When using the docker container, we need to change
                // the HOME path to WORKSPACE to have the authority
                // to install the packages.
                // There is the workaround of MTM1M3 xml version here for the alias tag
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        git clone --branch develop https://github.com/lsst-ts/ts_config_mttcs
                        cd ${env.SAL_USERS_HOME}
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_REPOS}/ts_xml
                        git checkout 74ded62 sal_interfaces/MTM1M3/MTM1M3_Commands.xml
                        git checkout f57e9d1 sal_interfaces/MTM1M3/MTM1M3_Events.xml
                        make_idl_files.py MTAOS Hexapod MTM1M3 MTM2
                    """
                }
            }
        }

        stage('Unit Tests and Coverage Analysis') { 
            steps {
                // Direct the HOME to WORKSPACE for pip to get the
                // installed library.
                // 'PATH' can only be updated in a single shell block.
                // We can not update PATH in 'environment' block.
                // Pytest needs to export the junit report. 
                // Unset LSST_DDS_IP because Jenkins gives the value of '0'
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        cd ${env.SAL_USERS_HOME}
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.WORKSPACE}/ts_config_mttcs
                        setup -k -r .
                        cd ..
                        setup -k -r .
                        unset LSST_DDS_IP
                        pytest --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.XML_REPORT} tests/
                    """
                }
            }
        }
    }

    post {
        always {
            // Change the ownership of workspace to Jenkins for the clean up
            // This is a "work around" method
            withEnv(["HOME=${env.WORKSPACE}"]) {
                sh 'chown -R 1003:1003 ${HOME}/'
            }
            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit "${env.XML_REPORT}"

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
            ])
        }

        cleanup {
            // clean up the workspace
            deleteDir()
        }
    }
}
