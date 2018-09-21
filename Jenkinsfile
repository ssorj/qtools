pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'make clean build'
            }
        }

        stage('Test') {
            steps {
                sh 'make big-test'
            }
        }
    }
}
