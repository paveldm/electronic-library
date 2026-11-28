pipeline {
    agent any

    triggers {
        pollSCM('* * * * *')
    }

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
        timeout(time: 40, unit: 'MINUTES')
    }

    environment {
        IMAGE = 'electronic-library-pr4'
        CONTAINER = 'electronic-library-pr4'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --platform linux/arm64 --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" -t "$IMAGE:$BUILD_NUMBER" .
                    docker image inspect --format '{{.Os}}/{{.Architecture}}' "$IMAGE:$BUILD_NUMBER"
                '''
            }
        }

        stage('Deploy to Ubuntu with Ansible') {
            steps {
                sh '''
                    set -eu
                    image="$IMAGE:$BUILD_NUMBER"
                    revision=$(git rev-parse HEAD)
                    archive=$(mktemp "${TMPDIR:-/tmp}/library-pr5.XXXXXX")
                    trap 'rm -f "$archive"' EXIT
                    docker image save --output "$archive" "$image"
                    ansible-playbook -i ansible/inventory.ini ansible/deploy-image.yml \\
                        -e "image_ref=$image" -e "git_revision=$revision" \\
                        -e "image_archive='$archive'"
                '''
            }
        }
    }
}