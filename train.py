import tensorflow as tf
import transfer_model
from dataset import Dataset, ToyDataset
import argparse
import shutil
import numpy as np
import os

def val_to_summary(tag, value):
    return tf.Summary(value=[
        tf.Summary.Value(tag=tag, simple_value=value), 
    ])

def train():
    dataset = Dataset()
    test_images, test_labels = dataset.get_test_data()

    with tf.Graph().as_default():
        images_matrix_ph = tf.placeholder(tf.float32, shape=(None, 
            dataset.FEATURES['IMAGE_SIZE'] ** 2 * dataset.FEATURES['NUM_CHANNELS']))

        labels_ph = tf.placeholder(tf.int64, shape=(None))

        loaded_images_ph = tf.placeholder(tf.float32, 
            shape=(None, dataset.FEATURES['DESIRED_SIZE'], dataset.FEATURES['DESIRED_SIZE'], 3))

        input_drop = tf.placeholder(tf.float32)
        conv_drop = tf.placeholder(tf.float32)
        fc_drop = tf.placeholder(tf.float32)

        dropout_probs = {
            'input': input_drop,
            'conv': conv_drop,
            'fc': fc_drop
        }

        load_images = transfer_model.load_images(images_matrix_ph, dataset.FEATURES)

        augment_images = transfer_model.augment_images(images_matrix_ph, dataset.FEATURES)

        logits = transfer_model.inference(loaded_images_ph, dataset.FEATURES, dropout_probs)

        loss = transfer_model.loss(logits, labels_ph)

        train = transfer_model.training(loss, FLAGS.learning_rate)

        evaluation = transfer_model.evaluation(logits, labels_ph)

        summary = tf.summary.merge_all()

        writer = tf.summary.FileWriter(FLAGS.log_dir, graph=tf.get_default_graph())

        init = tf.global_variables_initializer()

        saver = tf.train.Saver()

        sess = tf.Session()

        sess.run(init)

        # used to log training, validation error to tensorboard
        def write_accuracy(tag, step, examples, labels):
            num_correct = 0

            for start in range(0, len(examples), FLAGS.batch_size):
                end = start + FLAGS.batch_size
                num_correct += sess.run(evaluation, 
                    feed_dict = { 
                        loaded_images_ph: sess.run(load_images, feed_dict={ images_matrix_ph : examples[start:end]}), 
                        labels_ph: labels[start:end],
                        input_drop: 1.0,
                        conv_drop: 1.0,
                        fc_drop: 1.0
                    })

            value = val_to_summary(tag, num_correct / len(test_labels))

            writer.add_summary(value, step)
            writer.flush()

        for step in range(FLAGS.steps):
            images, labels = dataset.get_minibatch(FLAGS.batch_size)

            images = sess.run(augment_images, feed_dict={ images_matrix_ph: images })

            if FLAGS.skip_dropout:
                feed_dict = {
                    loaded_images_ph: images, 
                    labels_ph: labels,
                    input_drop: 1.0,
                    conv_drop: 1.0,
                    fc_drop: 1.0
                }
            else:
                feed_dict = { 
                    loaded_images_ph: images, 
                    labels_ph: labels,
                    input_drop: FLAGS.input_dropout,
                    conv_drop: FLAGS.conv_dropout,
                    fc_drop: FLAGS.fc_dropout
                }

            _, loss_val = sess.run([train, loss], feed_dict=feed_dict)

            if step % 100 == 0:
                print('Step {0} and loss {1}'.format(step, loss_val))
                summary_str = sess.run(summary, feed_dict=feed_dict)
                writer.add_summary(summary_str, step)
                writer.flush()

            # calculate training accuracy and save the model
            if step % 2500 == 0:
                saver.save(sess, './models/cifar.ckpt', global_step=step)                        
                write_accuracy('train_accuracy', step, dataset.train_examples[:10000], dataset.train_labels[:10000])

            # calculate validation accuracy
            if step % 1000 == 0:
                write_accuracy('test_accuracy', step, test_images, test_labels)

def main(_):
    if FLAGS.wipe_logs and os.path.exists(FLAGS.log_dir):
        shutil.rmtree(FLAGS.log_dir)

    train()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '--learning_rate',
        type=float,
        default=0.0001,
        help='Initial learning rate.'
    )

    parser.add_argument(
        '--batch_size',
        type=int,
        default=100,
        help='Batch size.'
    )

    parser.add_argument(
        '--steps',
        type=int,
        default=10000,
        help='How many minibatch SGDs to run.'
    )

    parser.add_argument(
        '--input_dropout',
        type=float,
        default=0.90,
        help='Dropout keep probability for input layer'
    )

    parser.add_argument(
        '--conv_dropout',
        type=float,
        default=0.75,
        help='Dropout keep probability for convolutional layers'
    )

    parser.add_argument(
        '--fc_dropout',
        type=float,
        default=0.5,
        help='Dropout keep probability for fully connected layers'
    )

    parser.add_argument(
        '--skip_dropout',
        default=False,
        action='store_true',
        help='Use dropout or not'
    )

    parser.add_argument(
        '--log_dir',
        type=str,
        default='./logs',
        help='Dropout probability for input layer'
    )

    parser.add_argument(
        '--wipe_logs',
        default=False,
        action='store_true',
        help='Delete all logs.'
    )

    FLAGS, unparsed = parser.parse_known_args()
    tf.app.run(main=main, argv=unparsed)
