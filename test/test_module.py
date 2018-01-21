from aibs.eye_tracking import __main__
from aibs.eye_tracking.frame_stream import CvOutputStream, CvInputStream
import mock
import numpy as np
import os
import json
from skimage.draw import circle
import pytest


def image(shape=(200,200), cr_radius=10, cr_center=(100,100),
          pupil_radius=30, pupil_center=(100,100)):
    im = np.ones(shape, dtype=np.uint8)*128
    r, c = circle(pupil_center[0], pupil_center[1], pupil_radius, shape)
    im[r,c] = 0
    r, c = circle(cr_center[0], cr_center[1], cr_radius, shape)
    im[r,c] = 255
    return im


def input_stream(source):
    mock_istream = mock.MagicMock()
    mock_istream.num_frames = 2
    mock_istream.frame_shape = (200,200)
    mock_istream.__iter__ = mock.MagicMock(
        return_value=iter([np.zeros((200,200)), np.zeros((200,200))]))
    return mock_istream


@pytest.fixture()
def input_source(tmpdir_factory):
    filename = str(tmpdir_factory.mktemp("test").join('input.avi'))
    frame = image()
    ostream = CvOutputStream(filename, frame.shape[::-1], is_color=False)
    ostream.open(filename)
    for i in range(10):
        ostream.write(frame)
    ostream.close()
    return filename


@pytest.fixture()
def input_json(tmpdir_factory):
    filename = str(tmpdir_factory.mktemp("test").join('input.json'))
    output_dir = str(tmpdir_factory.mktemp("test"))
    annotation_file = str(tmpdir_factory.mktemp("test").join('anno.avi'))
    in_json = ('{"starburst": { }, "ransac": { }, "eye_params": { },'
               '"qc": {"generate_plots": false, "output_dir": "%s"}, '
               '"annotation": {"annotate_movie": false, "output_file": "%s"}, '
               '"cr_bounding_box": [], "pupil_bounding_box": [], '
               '"output_dir": "%s"}') % (output_dir, annotation_file,
                                         output_dir)
    with open(filename, "w") as f:
        f.write(in_json)
    return str(filename)


def assert_output(output_dir, annotation_file=None, qc_output_dir=None,
                  output_json=None):
    cr = np.load(os.path.join(output_dir, "cr_params.npy"))
    pupil = np.load(os.path.join(output_dir, "pupil_params.npy"))
    assert(os.path.exists(os.path.join(output_dir, "mean_frame.png")))
    assert(cr.shape == (10,5))
    assert(pupil.shape == (10,5))
    if annotation_file:
        check = CvInputStream(annotation_file)
        assert(check.num_frames == 10)
        check.close()
    if output_json:
        assert(os.path.exists(output_json))
    if qc_output_dir:
        assert(os.path.join(output_dir, "cr_all.png"))


def test_main_valid(input_source, input_json):
    args = ["aibs.eye_tracking", "--input_json", input_json,
            "--input_source", input_source]
    with open(input_json, "r") as f:
        json_data = json.load(f)
    output_dir = json_data["output_dir"]
    with mock.patch('sys.argv', args):
        __main__.main()
        assert_output(output_dir)
    out_json = os.path.join(output_dir, "output.json")
    args.extend(["--qc.generate_plots", "True",
                 "--annotation.annotate_movie", "True",
                 "--output_json", out_json])
    with mock.patch('sys.argv', args):
        __main__.main()
        assert_output(output_dir,
                      annotation_file=json_data["annotation"]["output_file"],
                      qc_output_dir=json_data["qc"]["output_dir"],
                      output_json=out_json)
    __main__.plt.close("all")


def test_main_invalid():
    with mock.patch("sys.argv", ["aibs.eye_tracking"]):
        with mock.patch("argparse.ArgumentParser.print_help") as mock_print:
            __main__.main()
            mock_print.assert_called_once()