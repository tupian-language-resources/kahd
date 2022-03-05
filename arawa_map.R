library(ggmap)
library(ggrepel)
araw <- read.csv("anaw.tsv", sep="\t")

location = c(-79.09056, -28.46552, -34.67249, 5.522895)

brazil = get_map(location = location, source = "osm")

brazilMap = ggmap(brazil)

brazilMap + geom_point(data=araw, aes(x=Longitude, y=Latitude), alpha=0.90, color=c("darkorange", "blueviolet", "#333FA0", "red", "pink", "antiquewhite3", "darkred", "darksalmon"), cex=4.5) + # plot the points
  labs(x="Latitude", y="Longitude") + # label the axes
  geom_label_repel(data = araw, size=4.5, fill = "bisque2",
                  xlim = c(NA, Inf),
                  ylim = c(-Inf, Inf), 
                  point.padding = 0,
                  box.padding = 0.70, max.overlaps = Inf, 
                  aes(label = Language, x = Longitude, y = Latitude), hjust = 0) +
theme_bw() + theme(legend.position="bottom", axis.text = element_text(size = rel(0.90)), legend.key = element_rect(colour = "white"), axis.text.x = element_text(angle=45, vjust=0.5)) # tweak the plot's appearance and legend position
