#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        // Use the label to assign the node to run the test.
        // It is recommended by SQUARE team do not add the label.
        docker {
            image 'lsstts/aos_sal:latest'
            args "-u root --entrypoint=''"
        }
    }

    triggers {
        pollSCM('H * * * *')
    }

    environment {
        // SAL user home
        SAL_USERS_HOME = "/home/saluser"
        // SAL setup file
        SAL_SETUP_FILE = "/home/saluser/.setup.sh"
        // SAL-related repositories directory
        SAL_REPOS = "/home/saluser/repos"
        // XML report path
        XML_REPORT = "jenkinsReport/report.xml"
        // Module name used in the pytest coverage analysis
        MODULE_NAME = "lsst.ts.MTAOS"
        // SIMulated version
        SIMS_VERSION = "current"
        // Target branch - either develop or master, depending on where we are merging or what
        // branch is run
        BRANCH = getBranchName(env.CHANGE_TARGET, env.BRANCH_NAME)
    }

    stages {

        stage('Cloning repos') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        cd ${env.SAL_REPOS}
    
                        git clone -b master https://github.com/lsst-dm/phosim_utils.git
                        git clone -b ${BRANCH} https://github.com/lsst-ts/ts_wep.git
                        git clone -b ${BRANCH} https://github.com/lsst-ts/ts_ofc.git
                        git clone -b ${BRANCH} https://github.com/lsst-ts/ts_phosim.git
                    """
                }
            }
        }

        stage('Building ts_wep C++ interface') {
            steps {
                withEnv(["HOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_REPOS}

                        cd phosim_utils
                        setup -r . -t ${env.SIMS_VERSION}
                        scons
                        cd ..

                        cd ts_wep
                        setup -k -r .
                        scons
                        cd ..
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
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_REPOS}
    
                        cd phosim_utils
                        setup -r . -t ${env.SIMS_VERSION}
                        cd ..
    
                        cd ts_wep
                        setup -k -r .
                        cd ..
    
                        cd ts_ofc
                        setup -k -r .
                        cd ..
    
                        cd ts_phosim
                        setup -k -r .
                        cd ..

                        cd ${env.SAL_REPOS}/ts_config_mttcs
                        setup -k -r .

                        cd ${env.WORKSPACE}
                        setup -k -r .
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

// Return branch name. If changeTarget isn't defined, use branchName. Returns 
// either develop or master
def getBranchName(changeTarget, branchName) {
    def branch = (changeTarget != null) ? changeTarget : branchName
    // if not master or develop, it's ticket branch and so the main branch is
    // develop. Can be adjusted with hotfix branches merging into master
    // if (branch.startsWith("hotfix")) { return "master" }
    switch (branch) {
        case "master":
        case "develop":
            return branch
    }
    print("!!! Returning default for branch " + branch + " !!!\n")
    return "develop"
}
