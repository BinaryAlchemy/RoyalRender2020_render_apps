import os
from xml.etree.ElementTree import ElementTree, Element, SubElement


def all_forward_slashes(filepath):
    return os.path.normpath(filepath).replace('\\', '/')



class Clip:
    def __init__(self, job) -> None:
        self.start = int(job.seqStart)
        self.end = int(job.seqEnd)

        self.outdir = job.imageDir

        frnumprefix = self.get_frnum_prefix(job.imageFileName)
        self.outfile = f"{job.imageFileName[:-len(frnumprefix)]}[{frnumprefix}{self.start:0{job.imageFramePadding}}-{frnumprefix}{self.end:0{job.imageFramePadding}}{job.imageExtension}]"
        
        self.image_width = job.imageWidth
        self.image_height = job.imageHeight

    def get_frnum_prefix(self, image_file_name):
        prenumber_digits = []
        for d in reversed(image_file_name):
            if not d.isdigit():
                break

            prenumber_digits.append(d)
        
        return ''.join(reversed(prenumber_digits))

    @property
    def duration(self):
        return self.end - self.start + 1

    @property
    def pathurl(self):

        ret = all_forward_slashes(os.path.join(self.outdir, self.outfile))
        if self.outdir[1] == ":":
            ret = "file://localhost/" + ret

        return ret


class TimelineXml:

    def __init__(self, output_path, rate=24) -> None:
        self.job_outputs = dict(video=[], audio=[])

        self.rate = rate
        self.output_path = output_path

        self.root = self.create_xml_root()
        self.duration = self.compute_duration()

        self.create_timeline()
    
    def compute_duration(self):
        start_frame = 0
        end_frame = 0

        # TODO: sort jobs first!
        for i in range(rr.jobSelected_count()):
            job = rr.jobSelected_get(i)
            start_frame = min(start_frame, job.seqStart)
            end_frame = max(start_frame, job.seqEnd)

            # TODO: if audio
            self.job_outputs['video'].append(Clip(job))

        return int(end_frame - start_frame + 1)

    def create_xml_root(self):
        rootElement = Element("xmeml")
        rootElement.attrib["version"] = "5"
        
        return rootElement
    
    @staticmethod
    def add_key_text(parent, keyword, text):
        sub = SubElement(parent, keyword)
        sub.text = str(text)
        return sub

    def create_timeline(self):
        sequence = SubElement(self.root, "sequence")
        self.add_key_text(sequence, "name", "RR Timeline")
        self.add_key_text(sequence, "duration", self.duration)

        rate = SubElement(sequence, "rate")
        self.add_key_text(rate, "timebase", self.rate)

        self.add_media(sequence)
    
    def add_media(self, sequence):
        media = SubElement(sequence, "media")
        for output_type, output in self.job_outputs.items():
            audio_video = SubElement(media, output_type)
            track = SubElement(audio_video, "track")

            last_end = 0

            for out_clip in output:
                clipitem = SubElement(track, "clipitem", attrib={"id": f"{out_clip.outfile} 0"})
                self.add_key_text(clipitem, "name", out_clip.outfile)
                self.add_key_text(clipitem, "duration", out_clip.duration)
                rate_item = SubElement(clipitem, "rate")
                self.add_key_text(rate_item, "timebase", self.rate)
                self.add_key_text(clipitem, "start", out_clip.start)
                self.add_key_text(clipitem, "end", out_clip.end)
                self.add_key_text(clipitem, "enabled", "True")

                self.add_key_text(clipitem, "in", last_end)
                last_end += out_clip.duration
                self.add_key_text(clipitem, "out", last_end)

                file_item = SubElement(clipitem, "file", attrib={"id": f"{out_clip.outfile} 2"})
                self.add_key_text(file_item, "duration", out_clip.duration)
                
                rate_item = SubElement(file_item, "rate")
                self.add_key_text(rate_item, "timebase", self.rate)
                
                self.add_key_text(file_item, "name", out_clip.outfile)
                self.add_key_text(file_item, "pathurl", out_clip.pathurl)

                file_media_item = SubElement(file_item, "media")
                file_type_item = SubElement(file_media_item, output_type)
                self.add_key_text(file_type_item, "duration", out_clip.duration)
                file_type_sample = SubElement(file_type_item, "samplecharacteristics")
                self.add_key_text(file_type_sample, "with", out_clip.image_width)
                self.add_key_text(file_type_sample, "height", out_clip.image_height)

                self.add_key_text(clipitem, "compositemode", "normal")


    # from infix.se (Filip Solomonsson)
    def indent(self, elem, level=0):
        i = "\n" + level * ' '
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + " "
            for e in elem:
                self.indent(e, level + 1)
                if not e.tail or not e.tail.strip():
                    e.tail = i + " "
            if not e.tail or not e.tail.strip():
                e.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
        return True

    def export_xml(self):
        if not self.output_path:
            print("No valid file has been passed to the write function")
            return False

        xml = ElementTree(self.root)
        self.indent(xml.getroot())

        with open(self.output_path, "wb") as f:
            xml.write(f)

        return True


if __name__ == '__main__':
    timeline = TimelineXml(r"D:\MIGHTY_STORAGE\timeline_test.xml")
    timeline.export_xml()
