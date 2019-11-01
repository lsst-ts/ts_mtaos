#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        // Use the label to assign the node to run the test.
        // It is recommended by SQUARE team do not add the label.
        docker {
            image 'lsstts/mtaos_dev:v0.3'
            args '-u root'
        }
    }

    triggers {
        pollSCM('H * * * *')
    }

    environment {
        // Position of LSST stack directory
        LSST_STACK="/opt/lsst/software/stack"
        // AOS repositories directory
        AOS_REPOS="/home/lsst/aos_repos"
        // SAL-related repositories directory
        SAL_REPOS="/home/lsst/repos"
        // SAL-related environment variables
        LSST_SDK_INSTALL="/home/lsst/repos/ts_sal"
        OSPL_HOME="/home/lsst/repos/ts_opensplice/OpenSpliceDDS/V6.9.0/HDE/x86_64.linux-debug"
        PYTHON_BUILD_VERSION="3.7m"
        PYTHON_BUILD_LOCATION="/opt/lsst/software/stack/python/miniconda3-4.5.12/envs/lsst-scipipe-1172c30"
        LSST_DDS_DOMAIN="mtaos"
        // XML report path
        XML_REPORT="jenkinsReport/report.xml"
        // Module name used in the pytest coverage analysis
        MODULE_NAME="lsst.ts.MTAOS"
    }

    stages {

        stage('Unit Tests and Coverage Analysis') { 
            steps {
                // Direct the HOME to WORKSPACE for pip to get the
                // installed library.
                // 'PATH' can only be updated in a single shell block.
                // We can not update PATH in 'environment' block.
                // Pytest needs to export the junit report. 
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source /opt/rh/devtoolset-6/enable
                        source ${env.LSST_STACK}/loadLSST.bash
                        cd ${AOS_REPOS}/phosim_utils
                        setup -k -r . -t sims_w_2019_20
                        cd ${AOS_REPOS}/ts_wep
                        setup -k -r .
                        cd ${AOS_REPOS}/ts_ofc
                        setup -k -r .
                        cd ${SAL_REPOS}/ts_xml
                        setup -k -r .
                        cd ${SAL_REPOS}/ts_sal
                        setup -k -r .
                        cd ${SAL_REPOS}/ts_config_ocs
                        setup -k -r .
                        cd ${SAL_REPOS}/ts_config_mttcs
                        setup -k -r .
                        cd ${SAL_REPOS}/ts_salobj
                        setup -k -r .
                        source ${SAL_REPOS}/ts_sal/setup.env
                        cd ${HOME}
                        setup -k -r .
                        pytest --ignore=tests/test_mtaosCsc.py --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.XML_REPORT} tests/
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
